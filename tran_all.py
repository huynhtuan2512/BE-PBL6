# ============================================================
# train_compare_40class.py
#
# MobileNetV3-Small training
#
# Dataset:
#   Dataset_40Class_Final/
#       Train/
#       Val/
#       Test/
#
# Features:
#   - CUDA
#   - tqdm
#   - ETA
#   - batch time
#   - GPU memory
#   - Early Stopping
#   - Save best model
#   - Test Accuracy
#   - Precision / Recall / F1
#   - Macro + Weighted
#   - Training time
#   - Test time
#   - Confusion Matrix
#   - Classification Report
#   - Drink metrics
#   - JSON training results
# ============================================================


import os
import json
import io
import time
import copy
import random

import numpy as np
from PIL import Image, ImageFilter

import torch
import torch.nn as nn
import torch.optim as optim

from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

from tqdm import tqdm

import matplotlib.pyplot as plt


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = r"D:\CODING\nam4_HK1\PBL6"

DATASET_DIR = os.path.join(
    BASE_DIR,
    "Dataset_30Class_Final"
)

TRAIN_DIR = os.path.join(
    DATASET_DIR,
    "Train"
)

VAL_DIR = os.path.join(
    DATASET_DIR,
    "Val"
)

TEST_DIR = os.path.join(
    DATASET_DIR,
    "Test"
)


MODEL_DIR = os.path.join(
    BASE_DIR,
    "Model_Comparison_40Class"
)

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ============================================================
# TRAIN CONFIG
# ============================================================

IMAGE_SIZE = 224

BATCH_SIZE = 32

NUM_WORKERS = 0

NUM_EPOCHS = 40

LEARNING_RATE = 0.0003

WEIGHT_DECAY = 1e-4

LABEL_SMOOTHING = 0.05

PATIENCE = 5

MIN_DELTA = 0.0005

# Regularization experiment: combine MixUp with augmentation and early stopping.
MIXUP_ALPHA = 0.1
MIXUP_PROBABILITY = 0.3
CLASSIFIER_DROPOUT = 0.25
CAMERA_QUALITY_PROBABILITY = 0.5
CAMERA_DOWNSCALE_RANGE = (0.40, 0.85)
CAMERA_JPEG_QUALITY_RANGE = (35, 80)
CAMERA_BLUR_PROBABILITY = 0.5
CAMERA_BLUR_RADIUS_RANGE = (0.2, 1.2)

SEED = 42

REQUIRE_CUDA = True


# ============================================================
# DRINK CLASSES
# ============================================================

DRINK_CLASSES = [
    "7up",
    "Aquafina - Nuoc Uong - Chai 500",
    "CocaCola",
    "Mirinda",
    "Pepsi",
    "Rockstar",
    "Sting red"
]


# ============================================================
# SEED
# ============================================================

def set_seed(seed=42):

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    torch.cuda.manual_seed_all(seed)

    # Giúp kết quả ổn định hơn
    torch.backends.cudnn.deterministic = True

    torch.backends.cudnn.benchmark = False


set_seed(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

if REQUIRE_CUDA and not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA is required for training, but this Python environment has no "
        "CUDA-enabled PyTorch. Run the script with the project .venv."
    )


# ============================================================
# PRINT DEVICE
# ============================================================

print()
print("=" * 90)
print("DEVICE")
print("=" * 90)

print("Device:", DEVICE)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )

    print(
        "CUDA:",
        torch.version.cuda
    )

else:

    print(
        "WARNING: CUDA not available."
    )


# ============================================================
# TRANSFORMS
# ============================================================

class RandomCameraQuality:
    """Simulate low-resolution, JPEG compression, and camera defocus."""

    def __call__(self, image):
        if random.random() >= CAMERA_QUALITY_PROBABILITY:
            return image

        width, height = image.size
        scale = random.uniform(*CAMERA_DOWNSCALE_RANGE)
        small_size = (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        )
        image = image.resize(small_size, Image.Resampling.BILINEAR)
        image = image.resize((width, height), Image.Resampling.BILINEAR)

        if random.random() < CAMERA_BLUR_PROBABILITY:
            image = image.filter(
                ImageFilter.GaussianBlur(
                    radius=random.uniform(*CAMERA_BLUR_RADIUS_RANGE)
                )
            )

        buffer = io.BytesIO()
        quality = random.randint(*CAMERA_JPEG_QUALITY_RANGE)
        image.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        with Image.open(buffer) as compressed:
            return compressed.convert("RGB")


train_transform = transforms.Compose([

    transforms.RandomResizedCrop(
        IMAGE_SIZE,
        scale=(0.80, 1.0),
    ),

    transforms.RandomHorizontalFlip(
        p=0.5
    ),

    transforms.RandomAffine(
        degrees=10,
        translate=(0.08, 0.08),
        scale=(0.85, 1.15),
        interpolation=transforms.InterpolationMode.BILINEAR,
        fill=(124, 116, 104),
    ),

    transforms.ColorJitter(
        brightness=0.15,
        contrast=0.15,
        saturation=0.15,
        hue=0.03
    ),

    transforms.RandomPerspective(
        distortion_scale=0.1,
        p=0.15
    ),

    RandomCameraQuality(),

    transforms.ToTensor(),

    transforms.RandomErasing(
        p=0.1,
    ),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


val_test_transform = transforms.Compose([

    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# LOAD DATASET
# ============================================================

print()
print("=" * 90)
print("LOADING DATASET")
print("=" * 90)


train_dataset = datasets.ImageFolder(
    TRAIN_DIR,
    transform=train_transform
)

train_eval_dataset = datasets.ImageFolder(
    TRAIN_DIR,
    transform=val_test_transform
)


val_dataset = datasets.ImageFolder(
    VAL_DIR,
    transform=val_test_transform
)


test_dataset = datasets.ImageFolder(
    TEST_DIR,
    transform=val_test_transform
)

print(train_dataset.classes)
print(train_dataset.class_to_idx)

class_counts = np.bincount(
    train_dataset.targets,
    minlength=len(train_dataset.classes)
).astype(np.float32)
if np.any(class_counts == 0):
    raise RuntimeError("Every class must contain at least one training image.")

# Moderate inverse-frequency weighting helps the small background class without
# allowing it to dominate the loss.
class_weights = np.sqrt(
    len(train_dataset) / (len(class_counts) * class_counts)
)
class_weights /= class_weights.mean()
print("Training class counts:", class_counts.astype(int).tolist())
print("Using balanced class weights for training.")
# ============================================================
# CHECK CLASS CONSISTENCY
# ============================================================

classes = train_dataset.classes

num_classes = len(classes)


print()
print("Number of classes:", num_classes)

print()


for i, class_name in enumerate(classes):

    print(
        f"{i:02d} -> {class_name}"
    )


if val_dataset.classes != classes:

    raise RuntimeError(
        "Train và Val có class khác nhau!"
    )


if test_dataset.classes != classes:

    raise RuntimeError(
        "Train và Test có class khác nhau!"
    )


# ============================================================
# DATALOADER
# ============================================================

train_loader = DataLoader(

    train_dataset,

    batch_size=BATCH_SIZE,

    shuffle=True,

    num_workers=NUM_WORKERS,

    pin_memory=torch.cuda.is_available()
)

train_eval_generator = torch.Generator()
train_eval_generator.manual_seed(SEED)

train_eval_loader = DataLoader(

    train_eval_dataset,

    batch_size=BATCH_SIZE,

    shuffle=False,

    num_workers=NUM_WORKERS,

    pin_memory=torch.cuda.is_available(),

    generator=train_eval_generator
)


val_loader = DataLoader(

    val_dataset,

    batch_size=BATCH_SIZE,

    shuffle=False,

    num_workers=NUM_WORKERS,

    pin_memory=torch.cuda.is_available()
)


test_loader = DataLoader(

    test_dataset,

    batch_size=BATCH_SIZE,

    shuffle=False,

    num_workers=NUM_WORKERS,

    pin_memory=torch.cuda.is_available()
)


# ============================================================
# DATASET SUMMARY
# ============================================================

print()
print("=" * 90)
print("DATASET SUMMARY")
print("=" * 90)

print(
    f"Train : {len(train_dataset):,}"
)

print(
    f"Train (evaluation, no augmentation) : "
    f"{len(train_eval_dataset):,}"
)

print(
    f"Val   : {len(val_dataset):,}"
)

print(
    f"Test  : {len(test_dataset):,}"
)

print(
    f"Total : "
    f"{len(train_dataset) + len(val_dataset) + len(test_dataset):,}"
)


# ============================================================
# MODEL: MOBILENETV3-SMALL
# ============================================================

def create_mobilenetv3_small(
    num_classes
):

    model = models.mobilenet_v3_small(
        weights=models.MobileNet_V3_Small_Weights.DEFAULT
    )


    in_features = (
        model.classifier[-1].in_features
    )


    model.classifier[-1] = nn.Sequential(

        nn.Dropout(
            p=CLASSIFIER_DROPOUT
        ),

        nn.Linear(
            in_features,
            num_classes
        )
    )


    return model


# ============================================================
# PARAMETER COUNT
# ============================================================

def count_parameters(model):

    return sum(
        p.numel()
        for p in model.parameters()
    )


def mixup_batch(
    images,
    labels
):
    """Blend each batch with a shuffled copy to improve generalization."""
    if MIXUP_ALPHA <= 0 or np.random.random() > MIXUP_PROBABILITY:
        return images, labels, labels, 1.0

    mixing = float(np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA))
    permutation = torch.randperm(images.size(0), device=images.device)
    mixed_images = mixing * images + (1.0 - mixing) * images[permutation]
    return mixed_images, labels, labels[permutation], mixing


# ============================================================
# TRAIN ONE EPOCH
# ============================================================

def train_one_epoch(
    model,
    loader,
    criterion,
    optimizer,
    epoch,
    total_epochs,
    model_name
):

    model.train()


    running_loss = 0.0

    correct = 0

    total = 0


    batch_times = []


    pbar = tqdm(

        loader,

        desc=(
            f"{model_name} | "
            f"Epoch {epoch}/{total_epochs}"
        ),

        unit="batch",

        dynamic_ncols=True
    )


    for batch_idx, (
        images,
        labels
    ) in enumerate(pbar):


        batch_start = time.time()


        images = images.to(
            DEVICE,
            non_blocking=True
        )

        labels = labels.to(
            DEVICE,
            non_blocking=True
        )


        optimizer.zero_grad(
            set_to_none=True
        )

        images, labels_a, labels_b, mixing = mixup_batch(
            images,
            labels
        )

        outputs = model(
            images
        )


        loss = (
            mixing * criterion(
                outputs,
                labels_a
            )
            + (1.0 - mixing) * criterion(
                outputs,
                labels_b
            )
        )


        loss.backward()


        optimizer.step()


        # ----------------------------------------------------
        # STATISTICS
        # ----------------------------------------------------

        batch_loss = loss.item()


        running_loss += (
            batch_loss *
            images.size(0)
        )


        _, predicted = outputs.max(
            1
        )


        total += labels.size(0)

        correct += (
            predicted == labels
        ).sum().item()


        batch_time = (
            time.time() -
            batch_start
        )


        batch_times.append(
            batch_time
        )


        current_loss = (
            running_loss /
            total
        )


        current_acc = (
            correct /
            total
        )


        # ----------------------------------------------------
        # GPU MEMORY
        # ----------------------------------------------------

        if torch.cuda.is_available():

            gpu_memory = (
                torch.cuda.memory_allocated()
                / 1024**3
            )

            gpu_peak = (
                torch.cuda.max_memory_allocated()
                / 1024**3
            )

        else:

            gpu_memory = 0

            gpu_peak = 0


        # ----------------------------------------------------
        # ETA
        # ----------------------------------------------------

        avg_batch_time = np.mean(
            batch_times
        )


        remaining_batches = (
            len(loader)
            -
            (batch_idx + 1)
        )


        eta_seconds = (
            avg_batch_time *
            remaining_batches
        )


        eta_minutes = (
            eta_seconds /
            60
        )


        pbar.set_postfix({

            "loss":
            f"{current_loss:.4f}",

            "batch_acc":
            f"{current_acc:.4f}",

            "batch":
            f"{batch_time:.2f}s",

            "GPU":
            f"{gpu_memory:.2f}GB",

            "peak":
            f"{gpu_peak:.2f}GB",

            "ETA":
            f"{eta_minutes:.1f}m"
        })


    epoch_loss = (
        running_loss /
        total
    )


    epoch_acc = (
        correct /
        total
    )


    avg_batch_time = np.mean(
        batch_times
    )


    peak_gpu_memory = 0


    if torch.cuda.is_available():

        peak_gpu_memory = (
            torch.cuda.max_memory_allocated()
            / 1024**3
        )


    return (
        epoch_loss,
        epoch_acc,
        avg_batch_time,
        peak_gpu_memory
    )


# ============================================================
# VALIDATION
# ============================================================

def validate(
    model,
    loader,
    criterion
):

    model.eval()


    running_loss = 0.0

    correct = 0

    total = 0


    start = time.time()


    with torch.no_grad():

        for images, labels in loader:

            images = images.to(
                DEVICE,
                non_blocking=True
            )

            labels = labels.to(
                DEVICE,
                non_blocking=True
            )


            outputs = model(
                images
            )


            loss = criterion(
                outputs,
                labels
            )


            running_loss += (
                loss.item() *
                images.size(0)
            )


            _, predicted = outputs.max(
                1
            )


            total += labels.size(0)

            correct += (
                predicted == labels
            ).sum().item()


    val_loss = (
        running_loss /
        total
    )


    val_acc = (
        correct /
        total
    )


    elapsed = (
        time.time() -
        start
    )


    return (
        val_loss,
        val_acc,
        elapsed
    )


# ============================================================
# TRAIN MODEL
# ============================================================

def train_model(
    model_name,
    model
):

    print()
    print()
    print("=" * 90)
    print(
        f"TRAINING: {model_name}"
    )
    print("=" * 90)


    model = model.to(
        DEVICE
    )


    parameters = count_parameters(
        model
    )


    print(
        f"Parameters: {parameters:,}"
    )
    print(
        "Regularization: "
        f"MixUp(alpha={MIXUP_ALPHA}, p={MIXUP_PROBABILITY}), "
        f"dropout={CLASSIFIER_DROPOUT}, "
        f"weight_decay={WEIGHT_DECAY}, "
        f"label_smoothing={LABEL_SMOOTHING}, "
        f"early_stopping_patience={PATIENCE}"
    )


    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(
            class_weights,
            dtype=torch.float32,
            device=DEVICE
        ),
        label_smoothing=LABEL_SMOOTHING
    )
    validation_criterion = nn.CrossEntropyLoss()


    optimizer = optim.AdamW(

        model.parameters(),

        lr=LEARNING_RATE,

        weight_decay=WEIGHT_DECAY
    )


    scheduler = optim.lr_scheduler.ReduceLROnPlateau(

        optimizer,

        mode="max",

        factor=0.5,

        patience=2
    )


    best_val_accuracy = 0.0

    best_epoch = 0

    best_state = None

    epochs_without_improvement = 0


    history = {

        "train_loss": [],

        "train_augmented_accuracy": [],

        "val_loss": [],

        "val_accuracy": [],

        "learning_rate": [],

        "epoch_time": [],

        "avg_batch_time": [],

        "peak_gpu_memory": []
    }


    total_training_start = time.time()


    for epoch in range(
        1,
        NUM_EPOCHS + 1
    ):

        if torch.cuda.is_available():

            torch.cuda.reset_peak_memory_stats()


        epoch_start = time.time()


        (
            train_loss,
            train_acc,
            avg_batch_time,
            peak_gpu
        ) = train_one_epoch(

            model,

            train_loader,

            criterion,

            optimizer,

            epoch,

            NUM_EPOCHS,

            model_name
        )

        (
            val_loss,
            val_acc,
            val_time
        ) = validate(

            model,

            val_loader,

            validation_criterion
        )


        scheduler.step(
            val_acc
        )


        current_lr = (
            optimizer.param_groups[0]["lr"]
        )


        epoch_time = (
            time.time() -
            epoch_start
        )


        # ----------------------------------------------------
        # HISTORY
        # ----------------------------------------------------

        history[
            "train_loss"
        ].append(
            train_loss
        )

        history[
            "train_augmented_accuracy"
        ].append(
            train_acc
        )

        history[
            "val_loss"
        ].append(
            val_loss
        )

        history[
            "val_accuracy"
        ].append(
            val_acc
        )

        history[
            "learning_rate"
        ].append(
            current_lr
        )

        history[
            "epoch_time"
        ].append(
            epoch_time
        )

        history[
            "avg_batch_time"
        ].append(
            avg_batch_time
        )

        history[
            "peak_gpu_memory"
        ].append(
            peak_gpu
        )


        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        print()
        print(
            f"{'=' * 25} "
            f"Epoch {epoch} SUMMARY "
            f"{'=' * 25}"
        )

        print(
            f"Train Loss (augmented batches) : "
            f"{train_loss:.4f}"
        )

        print(
            f"Batch Accuracy (training transforms/MixUp) : "
            f"{train_acc:.4f}"
        )

        print(
            f"Val Loss         : "
            f"{val_loss:.4f}"
        )

        print(
            f"Val Accuracy     : "
            f"{val_acc:.4f}"
        )

        print(
            f"Learning Rate    : "
            f"{current_lr:.6f}"
        )

        print(
            f"Epoch Time       : "
            f"{epoch_time / 60:.2f} min"
        )

        print(
            f"Avg Batch Time   : "
            f"{avg_batch_time:.3f}s"
        )

        print(
            f"Peak GPU Memory  : "
            f"{peak_gpu:.2f} GB"
        )

        print(
            f"Validation Time  : "
            f"{val_time:.2f}s"
        )

        # ----------------------------------------------------
        # BEST MODEL
        # ----------------------------------------------------

        if (
            val_acc >
            best_val_accuracy +
            MIN_DELTA
        ):

            best_val_accuracy = (
                val_acc
            )

            best_epoch = epoch

            best_state = copy.deepcopy(
                model.state_dict()
            )


            checkpoint_path = os.path.join(

                MODEL_DIR,

                f"{model_name}_best.pth"
            )


            torch.save({

                "model_name":
                model_name,

                "model_state_dict":
                best_state,

                "classes":
                classes,

                "num_classes":
                num_classes,

                "epoch":
                epoch,

                "val_accuracy":
                val_acc,

                "val_loss":
                val_loss,

                "parameters":
                parameters

            }, checkpoint_path)


            print()
            print(
                f"[BEST MODEL SAVED]"
            )

            print(
                f"Epoch: {epoch}"
            )

            print(
                f"Val Accuracy: "
                f"{val_acc:.4f}"
            )


            epochs_without_improvement = 0


        else:

            epochs_without_improvement += 1


        # ----------------------------------------------------
        # EARLY STOPPING
        # ----------------------------------------------------

        if (
            epochs_without_improvement
            >= PATIENCE
        ):

            print()
            print(
                "[EARLY STOPPING]"
            )

            print(
                f"No improvement "
                f"for {PATIENCE} epochs."
            )

            break


    total_training_time = (
        time.time() -
        total_training_start
    )


    # --------------------------------------------------------
    # RESTORE BEST
    # --------------------------------------------------------

    if best_state is not None:

        model.load_state_dict(
            best_state
        )

    print()
    print("Evaluating best checkpoint on original training images...")
    (
        train_original_loss,
        train_original_accuracy,
        train_original_eval_time
    ) = validate(
        model,
        train_eval_loader,
        validation_criterion
    )
    history["train_original_loss_final"] = train_original_loss
    history["train_original_accuracy_final"] = train_original_accuracy
    history["train_original_eval_time_seconds"] = train_original_eval_time
    history["best_epoch"] = best_epoch
    print(
        f"Final Train Accuracy (original images, best checkpoint): "
        f"{train_original_accuracy:.4f}"
    )
    print(
        f"Final Train Loss (original images): {train_original_loss:.4f}"
    )
    print(
        f"Final Train Evaluation Time: {train_original_eval_time:.2f}s"
    )


    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    history_path = os.path.join(

        MODEL_DIR,

        f"{model_name}_history.json"
    )


    with open(
        history_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            indent=4
        )


    return {

        "model": model,

        "parameters":
        parameters,

        "best_epoch":
        best_epoch,

        "best_val_accuracy":
        best_val_accuracy,

        "training_time_seconds":
        total_training_time,

        "history":
        history
    }


# ============================================================
# TEST MODEL
# ============================================================

def test_model(
    model_name,
    model
):

    print()
    print()
    print("=" * 90)
    print(
        f"TESTING: {model_name}"
    )
    print("=" * 90)


    model.eval()


    ys = []

    ps = []

    test_loss_total = 0.0

    total = 0


    criterion = nn.CrossEntropyLoss()


    start = time.time()


    with torch.no_grad():

        for images, labels in tqdm(

            test_loader,

            desc=f"{model_name} Testing",

            unit="batch",

            dynamic_ncols=True
        ):


            images = images.to(
                DEVICE,
                non_blocking=True
            )

            labels = labels.to(
                DEVICE,
                non_blocking=True
            )


            outputs = model(
                images
            )


            loss = criterion(
                outputs,
                labels
            )


            test_loss_total += (
                loss.item() *
                images.size(0)
            )


            predicted = outputs.argmax(
                dim=1
            )


            ys.extend(
                labels.cpu().numpy()
            )

            ps.extend(
                predicted.cpu().numpy()
            )


            total += labels.size(0)


    test_time = (
        time.time() -
        start
    )


    ys = np.array(
        ys
    )

    ps = np.array(
        ps
    )


    test_loss = (
        test_loss_total /
        total
    )


    # ========================================================
    # METRICS
    # ========================================================

    accuracy = accuracy_score(
        ys,
        ps
    )


    precision_weighted = precision_score(
        ys,
        ps,
        average="weighted",
        zero_division=0
    )


    recall_weighted = recall_score(
        ys,
        ps,
        average="weighted",
        zero_division=0
    )


    f1_weighted = f1_score(
        ys,
        ps,
        average="weighted",
        zero_division=0
    )


    precision_macro = precision_score(
        ys,
        ps,
        average="macro",
        zero_division=0
    )


    recall_macro = recall_score(
        ys,
        ps,
        average="macro",
        zero_division=0
    )


    f1_macro = f1_score(
        ys,
        ps,
        average="macro",
        zero_division=0
    )


    print()

    print(
        f"Test Loss              : "
        f"{test_loss:.4f}"
    )

    print(
        f"Test Accuracy          : "
        f"{accuracy:.4f}"
    )

    print(
        f"Precision Weighted     : "
        f"{precision_weighted:.4f}"
    )

    print(
        f"Recall Weighted        : "
        f"{recall_weighted:.4f}"
    )

    print(
        f"F1 Weighted            : "
        f"{f1_weighted:.4f}"
    )

    print(
        f"Precision Macro        : "
        f"{precision_macro:.4f}"
    )

    print(
        f"Recall Macro           : "
        f"{recall_macro:.4f}"
    )

    print(
        f"F1 Macro               : "
        f"{f1_macro:.4f}"
    )


    # ========================================================
    # CLASSIFICATION REPORT
    # ========================================================

    report = classification_report(

        ys,

        ps,

        target_names=classes,

        digits=4,

        zero_division=0
    )


    report_path = os.path.join(

        MODEL_DIR,

        f"{model_name}_classification_report.txt"
    )


    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            report
        )


    print()
    print(
        report
    )


    # ========================================================
    # CONFUSION MATRIX
    # ========================================================

    cm = confusion_matrix(

        ys,

        ps,

        labels=np.arange(
            num_classes
        )
    )


    np.save(

        os.path.join(

            MODEL_DIR,

            f"{model_name}_confusion_matrix.npy"
        ),

        cm
    )


    plot_confusion_matrix(

        cm,

        classes,

        f"{model_name} - Confusion Matrix",

        os.path.join(

            MODEL_DIR,

            f"{model_name}_confusion_matrix.png"
        ),

        normalized=False
    )


    plot_confusion_matrix(

        cm,

        classes,

        f"{model_name} - Confusion Matrix Normalized",

        os.path.join(

            MODEL_DIR,

            f"{model_name}_confusion_matrix_normalized.png"
        ),

        normalized=True
    )


    # ========================================================
    # DRINK METRICS
    # ========================================================

    drink_metrics = calculate_drink_metrics(

        ys,

        ps
    )


    print()
    print(
        "=" * 90
    )

    print(
        "DRINK METRICS"
    )

    print(
        "=" * 90
    )


    if drink_metrics is not None:

        print(
            f"Drink Accuracy  : "
            f"{drink_metrics['accuracy']:.4f}"
        )

        print(
            f"Drink Precision : "
            f"{drink_metrics['precision']:.4f}"
        )

        print(
            f"Drink Recall    : "
            f"{drink_metrics['recall']:.4f}"
        )

        print(
            f"Drink F1        : "
            f"{drink_metrics['f1']:.4f}"
        )

        print(
            f"Drink Samples   : "
            f"{drink_metrics['samples']}"
        )


    return {

        "test_loss":
        test_loss,

        "test_accuracy":
        accuracy,

        "test_precision_weighted":
        precision_weighted,

        "test_recall_weighted":
        recall_weighted,

        "test_f1_weighted":
        f1_weighted,

        "test_precision_macro":
        precision_macro,

        "test_recall_macro":
        recall_macro,

        "test_f1_macro":
        f1_macro,

        "test_time_seconds":
        test_time,

        "drink_metrics":
        drink_metrics
    }


# ============================================================
# DRINK METRICS
# ============================================================

def calculate_drink_metrics(
    ys,
    ps
):

    drink_indices = []

    for drink in DRINK_CLASSES:

        if drink in classes:

            drink_indices.append(
                classes.index(drink)
            )


    if len(drink_indices) == 0:

        return None


    drink_indices = np.array(
        drink_indices
    )


    mask = np.isin(
        ys,
        drink_indices
    )


    if not mask.any():

        return None


    drink_true = ys[
        mask
    ]

    drink_pred = ps[
        mask
    ]


    accuracy = accuracy_score(

        drink_true,

        drink_pred
    )


    precision = precision_score(

        drink_true,

        drink_pred,

        labels=drink_indices,

        average="macro",

        zero_division=0
    )


    recall = recall_score(

        drink_true,

        drink_pred,

        labels=drink_indices,

        average="macro",

        zero_division=0
    )


    f1 = f1_score(

        drink_true,

        drink_pred,

        labels=drink_indices,

        average="macro",

        zero_division=0
    )


    return {

        "accuracy":
        float(accuracy),

        "precision":
        float(precision),

        "recall":
        float(recall),

        "f1":
        float(f1),

        "samples":
        int(len(drink_true))
    }


# ============================================================
# CONFUSION MATRIX PLOT
# ============================================================

def plot_confusion_matrix(

    cm,

    names,

    title,

    save_path,

    normalized=False
):


    matrix = cm.astype(
        np.float64
    )


    if normalized:

        row_sum = matrix.sum(
            axis=1,
            keepdims=True
        )


        matrix = np.divide(

            matrix,

            row_sum,

            out=np.zeros_like(matrix),

            where=row_sum != 0
        )


    size = max(
        14,
        len(names) * 0.55
    )


    fig, ax = plt.subplots(

        figsize=(
            size,
            size
        )
    )


    im = ax.imshow(

        matrix,

        interpolation="nearest",

        aspect="auto"
    )


    fig.colorbar(
        im,
        ax=ax
    )


    ax.set_title(
        title
    )

    ax.set_xlabel(
        "Predicted"
    )

    ax.set_ylabel(
        "Actual"
    )


    ax.set_xticks(
        np.arange(
            len(names)
        )
    )

    ax.set_yticks(
        np.arange(
            len(names)
        )
    )


    ax.set_xticklabels(

        names,

        rotation=90,

        fontsize=7
    )


    ax.set_yticklabels(

        names,

        fontsize=7
    )


    # Chỉ hiện số nếu khác 0
    for i in range(
        len(names)
    ):

        for j in range(
            len(names)
        ):

            value = matrix[
                i,
                j
            ]


            if value != 0:

                if normalized:

                    text = (
                        f"{value:.2f}"
                    )

                else:

                    text = str(
                        int(value)
                    )


                ax.text(

                    j,

                    i,

                    text,

                    ha="center",

                    va="center",

                    fontsize=5
                )


    fig.tight_layout()


    fig.savefig(

        save_path,

        dpi=250,

        bbox_inches="tight"
    )


    plt.close(
        fig
    )


# ============================================================
# PLOT TRAINING HISTORY
# ============================================================

def plot_history(

    model_name,

    history
):


    epochs = range(

        1,

        len(
            history[
                "train_loss"
            ]
        ) + 1
    )


    # --------------------------------------------------------
    # LOSS
    # --------------------------------------------------------

    plt.figure(
        figsize=(10, 6)
    )


    plt.plot(

        epochs,

        history[
            "val_loss"
        ],

        label="Val Loss"
    )

    plt.scatter(
        [history["best_epoch"]],
        [history["train_original_loss_final"]],
        label="Train Loss (best checkpoint, evaluated once)",
        marker="o",
        zorder=3,
    )


    plt.xlabel(
        "Epoch"
    )

    plt.ylabel(
        "Loss"
    )

    plt.title(
        f"{model_name} - Loss"
    )

    plt.legend()

    plt.grid(
        True
    )


    plt.tight_layout()


    plt.savefig(

        os.path.join(

            MODEL_DIR,

            f"{model_name}_loss.png"
        ),

        dpi=200
    )


    plt.close()


    # --------------------------------------------------------
    # ACCURACY
    # --------------------------------------------------------

    plt.figure(
        figsize=(10, 6)
    )


    plt.plot(

        epochs,

        history[
            "val_accuracy"
        ],

        label="Val Accuracy"
    )

    plt.scatter(
        [history["best_epoch"]],
        [history["train_original_accuracy_final"]],
        label="Train Accuracy (best checkpoint, evaluated once)",
        marker="o",
        zorder=3,
    )


    plt.xlabel(
        "Epoch"
    )

    plt.ylabel(
        "Accuracy"
    )

    plt.title(
        f"{model_name} - Accuracy"
    )

    plt.legend()

    plt.grid(
        True
    )


    plt.tight_layout()


    plt.savefig(

        os.path.join(

            MODEL_DIR,

            f"{model_name}_accuracy.png"
        ),

        dpi=200
    )


    plt.close()


# ============================================================
# COMPARE MODELS
# ============================================================

def print_comparison(
    results
):


    print()
    print()
    print("=" * 110)
    print("MODEL COMPARISON")
    print("=" * 110)


    print()

    header = (

        f"{'Metric':<32}"

        f"{'ResNet18':>18}"

        f"{'MobileNetV3':>20}"
    )


    print(
        header
    )

    print(
        "-" * 110
    )


    metrics = [

        (
            "Parameters",

            "parameters",

            "{:,}"
        ),

        (
            "Best Epoch",

            "best_epoch",

            "{}"
        ),

        (
            "Best Val Accuracy",

            "best_val_accuracy",

            "{:.4f}"
        ),

        (
            "Test Accuracy",

            "test_accuracy",

            "{:.4f}"
        ),

        (
            "Weighted Precision",

            "test_precision_weighted",

            "{:.4f}"
        ),

        (
            "Weighted Recall",

            "test_recall_weighted",

            "{:.4f}"
        ),

        (
            "Weighted F1",

            "test_f1_weighted",

            "{:.4f}"
        ),

        (
            "Macro Precision",

            "test_precision_macro",

            "{:.4f}"
        ),

        (
            "Macro Recall",

            "test_recall_macro",

            "{:.4f}"
        ),

        (
            "Macro F1",

            "test_f1_macro",

            "{:.4f}"
        ),

        (
            "Training Time",

            "training_time_seconds",

            "{:.1f}s"
        ),

        (
            "Test Time",

            "test_time_seconds",

            "{:.1f}s"
        )
    ]


    for label, key, fmt in metrics:

        r = results[
            "ResNet18"
        ][key]

        m = results[
            "MobileNetV3-Small"
        ][key]


        if key == "parameters":

            r_text = (
                f"{r:,}"
            )

            m_text = (
                f"{m:,}"
            )

        elif key in [

            "best_epoch"

        ]:

            r_text = (
                f"{r}"
            )

            m_text = (
                f"{m}"
            )

        else:

            r_text = fmt.format(
                r
            )

            m_text = fmt.format(
                m
            )


        print(

            f"{label:<32}"

            f"{r_text:>18}"

            f"{m_text:>20}"
        )


    print(
        "-" * 110
    )


# ============================================================
# MAIN
# ============================================================

def main():


    print()
    print("=" * 90)
    print("MOBILENETV3-SMALL TRAINING")
    print("=" * 90)


    results = {}


    # ========================================================
    # MOBILENETV3
    # ========================================================

    mobilenet = create_mobilenetv3_small(
        num_classes
    )


    mobilenet_result = train_model(

        "MobileNetV3-Small",

        mobilenet
    )


    plot_history(

        "MobileNetV3-Small",

        mobilenet_result[
            "history"
        ]
    )


    mobilenet_test = test_model(

        "MobileNetV3-Small",

        mobilenet_result[
            "model"
        ]
    )


    results[
        "MobileNetV3-Small"
    ] = {

        "model":
        "MobileNetV3-Small",

        "parameters":
        mobilenet_result[
            "parameters"
        ],

        "best_epoch":
        mobilenet_result[
            "best_epoch"
        ],

        "best_val_accuracy":
        mobilenet_result[
            "best_val_accuracy"
        ],

        **mobilenet_test,

        "training_time_seconds":
        mobilenet_result[
            "training_time_seconds"
        ]
    }


    # ========================================================
    # SAVE JSON
    # ========================================================

    json_path = os.path.join(

        MODEL_DIR,

        "model_comparison_results.json"
    )


    with open(

        json_path,

        "w",

        encoding="utf-8"
    ) as f:

        json.dump(

            results,

            f,

            indent=4,

            ensure_ascii=False
        )


    # ========================================================
    # FINAL
    # ========================================================

    print()
    print()
    print("=" * 90)
    print("TRAINING COMPLETED")
    print("=" * 90)


    print()
    print(
        "Output folder:"
    )

    print(
        MODEL_DIR
    )


    print()
    print(
        "Files generated:"
    )

    print(" - MobileNetV3-Small_best.pth")
    print(" - MobileNetV3-Small_history.json")
    print(" - MobileNetV3-Small_classification_report.txt")
    print(" - MobileNetV3-Small_confusion_matrix.png")
    print(" - MobileNetV3-Small_confusion_matrix_normalized.png")
    print(" - MobileNetV3-Small_loss.png")
    print(" - MobileNetV3-Small_accuracy.png")

    print(
        " - model_comparison_results.json"
    )

    print("=" * 90)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()