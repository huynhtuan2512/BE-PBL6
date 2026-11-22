CREATE DATABASE restaurant_data;
USE restaurant_data;


-- =========================================================
-- PHẦN 1: TẠO CÁC BẢNG NỀN TẢNG (TABLE SCHEMAS)
-- =========================================================

-- 1. Quyền hạn
CREATE TABLE roles (
    role_id VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(30) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- 2. Người dùng
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    role_id VARCHAR(50) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

-- 3. Danh mục món ăn (Category)
CREATE TABLE categories (
    category_id VARCHAR(50) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- 4. Bàn ăn (Quản lý trạng thái bàn)
CREATE TABLE tables (
    table_id INT AUTO_INCREMENT PRIMARY KEY,
    table_number INT NOT NULL UNIQUE,       -- Số bàn robot nhận được từ server
    capacity INT DEFAULT 4,
    status VARCHAR(20) DEFAULT 'EMPTY' CHECK (status IN ('EMPTY', 'OCCUPIED', 'RESERVED', 'CLEANING')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Thực đơn
CREATE TABLE dishes (
    dish_id INT AUTO_INCREMENT PRIMARY KEY, -- Cũng là dish_id Raspberry gửi lên (nhãn nhận diện)
    category_id VARCHAR(50) NOT NULL,
    dish_name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    price DECIMAL(10, 2) NOT NULL,
    image_url VARCHAR(255),
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- 6. Đơn hàng (Orders)
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    table_id INT NOT NULL,
    created_by_user_id VARCHAR(50) NULL,
    total_amount DECIMAL(10, 2) DEFAULT 0,
    order_status VARCHAR(30) DEFAULT 'PENDING' CHECK (order_status IN ('PENDING', 'PREPARING', 'PROCESSING', 'DELIVERING', 'COMPLETED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES tables(table_id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 7. Chi tiết đơn hàng
CREATE TABLE order_details (
    detail_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    dish_id INT NOT NULL,
    quantity INT DEFAULT 1,
    price_at_time DECIMAL(10, 2) NOT NULL, -- Lưu giá món tại thời điểm đặt
    notes VARCHAR(255) NULL,                -- Ghi chú cho bếp (VD: "Không hành", "Ít cay")
    served_status BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id)
);

-- 8. Hóa đơn (Invoices)
CREATE TABLE invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL UNIQUE,
    user_id VARCHAR(50) NULL, -- Staff/Cashier lập hóa đơn
    total_amount DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    final_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(30) DEFAULT 'CASH' CHECK (payment_method IN ('CASH', 'BANK_TRANSFER', 'CREDIT_CARD', 'MOMO')),
    payment_status VARCHAR(20) DEFAULT 'PAID' CHECK (payment_status IN ('UNPAID', 'PAID', 'REFUNDED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 9. Nhật ký hệ thống (Audit Logs)
CREATE TABLE audit_logs (
    log_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NULL,
    action VARCHAR(50) NOT NULL,      -- VD: CREATE, UPDATE, DELETE, LOGIN
    table_name VARCHAR(50) NOT NULL,  -- Bảng chịu tác động
    description TEXT NULL,            -- Chi tiết thay đổi
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);


-- =========================================================
-- PHẦN 2: CÁC BẢNG ROBOT (THEO GIAO THỨC WEBSOCKET)
-- =========================================================

-- 10. Nhiệm vụ giao hàng (task_id do Raspberry sinh ra)
CREATE TABLE robot_tasks (
    robot_id VARCHAR(50) NOT NULL,
    task_id INT NOT NULL,
    dish_id INT NULL,
    detail_id VARCHAR(50) NULL UNIQUE,     -- Món trong đơn đang được task này giữ
    order_id VARCHAR(50) NULL,
    table_number INT NULL,
    task_status VARCHAR(30) DEFAULT 'WAITING_FOR_DISH' CHECK (task_status IN ('WAITING_FOR_DISH', 'DELIVERING', 'DELIVERED', 'FAILED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (robot_id, task_id),
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id),
    FOREIGN KEY (detail_id) REFERENCES order_details(detail_id) ON DELETE SET NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE SET NULL
);

-- 11. Món nhận diện được (action: send_detections)
CREATE TABLE robot_detections (
    detection_id VARCHAR(50) PRIMARY KEY,
    robot_id VARCHAR(50) NOT NULL,
    task_id INT NOT NULL,
    dish_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id),
    INDEX idx_robot_detection_task (robot_id, task_id, created_at)
);

-- 12. Ảnh tốt nhất của task (action: upload_best_image)
CREATE TABLE robot_best_images (
    image_id VARCHAR(50) NOT NULL UNIQUE,
    robot_id VARCHAR(50) NOT NULL,
    task_id INT NOT NULL,
    dish_id INT NULL,
    mime_type VARCHAR(100) NOT NULL,
    image_data LONGBLOB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (robot_id, task_id),
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id)
);

-- 13. Sự kiện / log (action: send_event)
CREATE TABLE robot_events (
    event_id VARCHAR(50) PRIMARY KEY,
    robot_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL DEFAULT 'INFO' CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_robot_events_time (robot_id, created_at)
);

-- 14. Trạng thái robot (action: send_status)
CREATE TABLE robot_state (
    robot_id VARCHAR(50) PRIMARY KEY,
    delivery_status VARCHAR(30) NOT NULL DEFAULT 'NOT_DELIVERED' CHECK (delivery_status IN ('NOT_DELIVERED', 'WAITING_FOR_DISH', 'DELIVERING', 'DELIVERED')),
    table_number INT NULL,
    order_id VARCHAR(50) NULL,
    obstacle_detected BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE SET NULL
);

-- 15. Lệnh từ server xuống robot (action: get_commands, acknowledge_command)
CREATE TABLE robot_commands (
    command_id VARCHAR(50) PRIMARY KEY,
    robot_id VARCHAR(50) NOT NULL,
    command ENUM('STOP','RETURN_TO_KITCHEN','RESET_STATUS') NOT NULL,
    payload_json LONGTEXT NULL,
    command_status ENUM('PENDING','DONE','FAILED') NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_robot_commands_pending (robot_id, command_status, created_at)
);

-- dish_id bắt đầu từ 0 nên phải tắt auto-increment-on-zero cho phiên này
-- (chạy cả file trong một lần/một phiên)
SET SESSION sql_mode = CONCAT(@@sql_mode, ',NO_AUTO_VALUE_ON_ZERO');


-- =========================================================
-- DỮ LIỆU MẪU
-- =========================================================

-- 1. Roles
INSERT INTO roles (role_id, role_name, description) VALUES
('ROLE_ADMIN', 'ADMIN', 'Quản trị hệ thống'),
('ROLE_STAFF', 'STAFF', 'Nhân viên phục vụ');

-- 2. Users (mật khẩu: admin123 / staff123 - bcrypt)
INSERT INTO users (user_id, role_id, username, password_hash, full_name, phone, is_active) VALUES
('USER_001', 'ROLE_ADMIN', 'admin',   '$2b$10$C/d5kNR6uU3LL7sscbKlKe4dMpEauWVWfOO7FrYP4hkM7FSucxyBm', 'Quản trị viên', '0900000001', TRUE),
('USER_002', 'ROLE_STAFF', 'staff01', '$2b$10$oStNrWA58P/dUp99THFZgu.NyZvmCf/3gT.0FOwav8uoVXCNH.ozW', 'Nhân viên 01', '0900000002', TRUE);

-- 3. Categories
INSERT INTO categories (category_id, category_name, description) VALUES
('CAT_VN_MAIN', 'Món chính Việt Nam', 'Bún, mì, cháo, cơm, gỏi cuốn...'),
('CAT_VN_BANH', 'Bánh Việt Nam',      'Các loại bánh truyền thống'),
('CAT_WESTERN', 'Món Âu - Mỹ',        'Fast food, pasta, pizza, sushi...'),
('CAT_DRINK',   'Nước giải khát',     'Nước ngọt, nước suối, nước tăng lực'),
('CAT_ALCOHOL', 'Đồ uống có cồn',     'Bia');

-- 4. Tables (10 bàn)
INSERT INTO tables (table_id, table_number, capacity, status) VALUES
(1,  1,  4, 'EMPTY'),
(2,  2,  4, 'OCCUPIED'),
(3,  3,  4, 'OCCUPIED'),
(4,  4,  4, 'EMPTY'),
(5,  5,  6, 'OCCUPIED'),
(6,  6,  6, 'EMPTY'),
(7,  7,  2, 'EMPTY'),
(8,  8,  2, 'EMPTY'),
(9,  9,  8, 'EMPTY'),
(10, 10, 8, 'EMPTY');

-- 5. Dishes (dish_id = nhãn AI của Raspberry; image_url trỏ tới thư mục uploads/dishes/ của server)
INSERT INTO dishes (dish_id, category_id, dish_name, description, price, image_url, is_available) VALUES
(0, 'CAT_DRINK', '7up', 'Nước ngọt 7up lon', 15000, '/uploads/dishes/7up.jpg', TRUE),
(1, 'CAT_DRINK', 'Aquafina - Nuoc Uong - Chai 500', 'Nước suối Aquafina chai 500ml', 10000, '/uploads/dishes/aquafina.jpg', TRUE),
(2, 'CAT_VN_BANH', 'Banh beo', 'Bánh bèo chén, tôm chấy, mỡ hành', 30000, '/uploads/dishes/banh_beo.jpg', TRUE),
(3, 'CAT_VN_BANH', 'Banh can', 'Bánh căn nướng khuôn đất', 35000, '/uploads/dishes/banh_can.jpg', TRUE),
(4, 'CAT_VN_BANH', 'Banh chung', 'Bánh chưng nhân đậu thịt', 40000, '/uploads/dishes/banh_chung.jpg', TRUE),
(5, 'CAT_VN_BANH', 'Banh cuon', 'Bánh cuốn nhân thịt, chả lụa', 35000, '/uploads/dishes/banh_cuon.jpg', TRUE),
(6, 'CAT_VN_BANH', 'Banh gio', 'Bánh giò nhân thịt nấm mèo', 25000, '/uploads/dishes/banh_gio.jpg', TRUE),
(7, 'CAT_VN_BANH', 'Banh khot', 'Bánh khọt tôm, nước mắm chua ngọt', 45000, '/uploads/dishes/banh_khot.jpg', TRUE),
(8, 'CAT_VN_BANH', 'Banh mi', 'Bánh mì thịt nguội, pate', 20000, '/uploads/dishes/banh_mi.jpg', TRUE),
(9, 'CAT_VN_BANH', 'Banh pia', 'Bánh pía nhân đậu xanh sầu riêng', 30000, '/uploads/dishes/banh_pia.jpg', TRUE),
(10, 'CAT_VN_BANH', 'Banh tet', 'Bánh tét nhân đậu thịt', 40000, '/uploads/dishes/banh_tet.jpg', TRUE),
(11, 'CAT_VN_BANH', 'Banh trang nuong', 'Bánh tráng nướng trứng, hành phi', 25000, '/uploads/dishes/banh_trang_nuong.jpg', TRUE),
(12, 'CAT_VN_BANH', 'Banh xeo', 'Bánh xèo tôm thịt, rau sống', 50000, '/uploads/dishes/banh_xeo.jpg', TRUE),
(13, 'CAT_VN_MAIN', 'Bun dau mam tom', 'Bún đậu mắm tôm, chả cốm, dồi', 55000, '/uploads/dishes/bun_dau_mam_tom.jpg', TRUE),
(14, 'CAT_VN_MAIN', 'Bun thit nuong', 'Bún thịt nướng, chả giò, rau sống', 50000, '/uploads/dishes/bun_thit_nuong.jpg', TRUE),
(15, 'CAT_VN_MAIN', 'Ca kho to', 'Cá kho tộ ăn kèm cơm', 85000, '/uploads/dishes/ca_kho_to.jpg', TRUE),
(16, 'CAT_VN_MAIN', 'Cao lau', 'Cao lầu Hội An, thịt xíu', 45000, '/uploads/dishes/cao_lau.jpg', TRUE),
(17, 'CAT_VN_MAIN', 'Chao long', 'Cháo lòng heo, hành phi', 35000, '/uploads/dishes/chao_long.jpg', TRUE),
(18, 'CAT_DRINK', 'CocaCola', 'Nước ngọt CocaCola lon', 15000, '/uploads/dishes/cocacola.jpg', TRUE),
(19, 'CAT_VN_MAIN', 'Com tam', 'Cơm tấm sườn bì chả', 50000, '/uploads/dishes/com_tam.jpg', TRUE),
(20, 'CAT_VN_MAIN', 'Goi cuon', 'Gỏi cuốn tôm thịt, nước chấm', 35000, '/uploads/dishes/goi_cuon.jpg', TRUE),
(21, 'CAT_ALCOHOL', 'Heineken', 'Bia Heineken lon', 25000, '/uploads/dishes/heineken.jpg', TRUE),
(22, 'CAT_VN_MAIN', 'Mi quang', 'Mì Quảng tôm thịt, bánh tráng', 45000, '/uploads/dishes/mi_quang.jpg', TRUE),
(23, 'CAT_DRINK', 'Mirinda', 'Nước ngọt Mirinda lon', 15000, '/uploads/dishes/mirinda.jpg', TRUE),
(24, 'CAT_DRINK', 'Pepsi', 'Nước ngọt Pepsi lon', 15000, '/uploads/dishes/pepsi.jpg', TRUE),
(25, 'CAT_DRINK', 'Rockstar', 'Nước tăng lực Rockstar', 20000, '/uploads/dishes/rockstar.jpg', TRUE),
(26, 'CAT_DRINK', 'Sting red', 'Nước tăng lực Sting đỏ', 15000, '/uploads/dishes/sting_red.jpg', TRUE),
(27, 'CAT_VN_MAIN', 'Xoi xeo', 'Xôi xéo đậu xanh, hành phi', 25000, '/uploads/dishes/xoi_xeo.jpg', TRUE),
(28, 'CAT_WESTERN', 'french_fries', 'Khoai tây chiên', 40000, '/uploads/dishes/french_fries.jpg', TRUE),
(29, 'CAT_WESTERN', 'fried_rice', 'Cơm chiên', 55000, '/uploads/dishes/fried_rice.jpg', TRUE),
(30, 'CAT_WESTERN', 'hamburger', 'Hamburger bò phô mai', 75000, '/uploads/dishes/hamburger.jpg', TRUE),
(31, 'CAT_WESTERN', 'hot_dog', 'Hot dog xúc xích', 45000, '/uploads/dishes/hot_dog.jpg', TRUE),
(32, 'CAT_WESTERN', 'lasagna', 'Lasagna thịt bò', 95000, '/uploads/dishes/lasagna.jpg', TRUE),
(33, 'CAT_WESTERN', 'pancakes', 'Bánh pancake mật ong', 60000, '/uploads/dishes/pancakes.jpg', TRUE),
(34, 'CAT_WESTERN', 'pizza', 'Pizza phô mai', 120000, '/uploads/dishes/pizza.jpg', TRUE),
(35, 'CAT_WESTERN', 'ramen', 'Mì ramen Nhật', 85000, '/uploads/dishes/ramen.jpg', TRUE),
(36, 'CAT_WESTERN', 'spaghetti_bolognese', 'Mì Ý sốt bò bằm', 90000, '/uploads/dishes/spaghetti_bolognese.jpg', TRUE),
(37, 'CAT_WESTERN', 'steak', 'Bò bít tết', 180000, '/uploads/dishes/steak.jpg', TRUE),
(38, 'CAT_WESTERN', 'sushi', 'Sushi cá hồi', 110000, '/uploads/dishes/sushi.jpg', TRUE),
(39, 'CAT_WESTERN', 'waffles', 'Bánh waffle trái cây', 65000, '/uploads/dishes/waffles.jpg', TRUE);

-- 6. Orders (ORDER_001 và ORDER_002 cùng có Banh khot -> dish_id 7 sẽ ra ORDER_001 trước)
INSERT INTO orders (order_id, table_id, created_by_user_id, total_amount, order_status, created_at) VALUES
('ORDER_001', 5, 'USER_002', 75000, 'PROCESSING', '2026-11-02 11:00:00'),
('ORDER_002', 3, 'USER_002', 95000, 'PROCESSING', '2026-11-02 11:05:00'),
('ORDER_003', 2, 'USER_002', 150000, 'PENDING',    '2026-11-02 11:10:00');

-- 7. Order details
INSERT INTO order_details (detail_id, order_id, dish_id, quantity, price_at_time, notes, served_status) VALUES
('DETAIL_001', 'ORDER_001', 7, 1, 45000, NULL, FALSE),
('DETAIL_002', 'ORDER_001', 24, 2, 15000, NULL, FALSE),
('DETAIL_003', 'ORDER_002', 7, 1, 45000, 'Ít cay', FALSE),
('DETAIL_004', 'ORDER_002', 19, 1, 50000, NULL, FALSE),
('DETAIL_005', 'ORDER_003', 34, 1, 120000, NULL, FALSE),
('DETAIL_006', 'ORDER_003', 0, 2, 15000, NULL, FALSE);

-- 8. Robot: trạng thái ban đầu và lệnh mẫu
INSERT INTO robot_state (robot_id, delivery_status, table_number, order_id, obstacle_detected) VALUES
('R01', 'NOT_DELIVERED', NULL, NULL, FALSE);

INSERT INTO robot_commands (command_id, robot_id, command, payload_json, command_status) VALUES
('C1', 'R01', 'STOP', '{}', 'PENDING');