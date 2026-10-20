-- =========================================================
-- PHẦN 0: RESET VÀ KHỞI TẠO LẠI DATABASE
-- =========================================================
DROP DATABASE IF EXISTS restaurant_db;
CREATE DATABASE restaurant_db;
USE restaurant_db;


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
    table_id VARCHAR(50) PRIMARY KEY,
    table_number INT NOT NULL UNIQUE,
    capacity INT DEFAULT 4,
    status VARCHAR(20) DEFAULT 'EMPTY' CHECK (status IN ('EMPTY', 'OCCUPIED', 'RESERVED', 'CLEANING')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Thực đơn
CREATE TABLE dishes (
    dish_id VARCHAR(50) PRIMARY KEY,
    category_id VARCHAR(50) NOT NULL,
    dish_name VARCHAR(100) NOT NULL,
    description TEXT NULL, -- Mô tả thành phần / hương vị món ăn
    price DECIMAL(10, 2) NOT NULL,
    image_url VARCHAR(255),
    ai_label_id VARCHAR(50),
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- 6. Đơn hàng (Orders)
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    table_id VARCHAR(50) NOT NULL,
    created_by_user_id VARCHAR(50) NULL,
    total_amount DECIMAL(10, 2) DEFAULT 0,
    order_status VARCHAR(30) DEFAULT 'PENDING' CHECK (order_status IN ('PENDING', 'PROCESSING', 'DELIVERING', 'COMPLETED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES tables(table_id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 7. Chi tiết đơn hàng
CREATE TABLE order_details (
    detail_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    dish_id VARCHAR(50) NOT NULL,
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
-- PHẦN 2: NẠP DỮ LIỆU MẪU (SEED DATA)
-- =========================================================

-- 1. Roles
INSERT INTO roles (role_id, role_name, description) VALUES 
('ROLE_01', 'ADMIN', 'Quản trị viên hệ thống'),
('ROLE_02', 'STAFF', 'Nhân viên phục vụ'),
('ROLE_03', 'CUSTOMER', 'Khách hàng tại bàn');

-- 2. Users
INSERT INTO users (user_id, role_id, username, password_hash, full_name, phone) VALUES 
('USER_01', 'ROLE_01', 'admin', 'hash_admin_123', 'Nguyễn Văn Admin', '0905123456'),
('USER_02', 'ROLE_02', 'staff01', 'hash_staff_123', 'Trần Thị Nhân Viên', '0905654321');

-- 3. Categories
INSERT INTO categories (category_id, category_name, description) VALUES
('CAT_01', 'Món Chính', 'Các món ăn chính như Cơm, Phở, Mỳ'),
('CAT_02', 'Đồ Uống', 'Nước giải khát, trà, cà phê');

-- 4. Tables
INSERT INTO tables (table_id, table_number, capacity, status) VALUES 
('TABLE_01', 1, 4, 'OCCUPIED'),
('TABLE_02', 2, 4, 'EMPTY'),
('TABLE_03', 3, 2, 'EMPTY'),
('TABLE_04', 4, 6, 'RESERVED'),
('TABLE_05', 5, 4, 'OCCUPIED'),
('TABLE_06', 6, 8, 'CLEANING');

-- 5. Dishes
INSERT INTO dishes (dish_id, category_id, dish_name, description, price, image_url, ai_label_id) VALUES 
('DISH_01', 'CAT_01', 'Phở Bò Đặc Biệt',     'Nước dùng hầm xương 12 tiếng, kèm tái, nạm, gầu', 55000, 'https://example.com/pho.jpg',     'pho_bo'),
('DISH_02', 'CAT_01', 'Cơm Chiên Dương Châu', 'Cơm chiên hạt ngọc, xá xíu, tôm tươi, đậu hà lan', 45000, 'https://example.com/com.jpg',     'com_chien'),
('DISH_03', 'CAT_01', 'Mì Quảng Gà',         'Mì Quảng truyền thống thịt gà ta xé sợi',         50000, 'https://example.com/mi.jpg',      'mi_quang'),
('DISH_04', 'CAT_02', 'Trà Đào Cam Sả',       'Trà đào tươi mát kết hợp vị cam và sả thơm nhẹ',  25000, 'https://example.com/tradao.jpg',  'tra_dao');

-- 6. Order Test (Đơn hàng tại Bàn 5)
INSERT INTO orders (order_id, table_id, created_by_user_id, total_amount, order_status) VALUES 
('ORD_1001', 'TABLE_05', 'USER_02', 105000, 'DELIVERING');

-- 7. Order Details Test
INSERT INTO order_details (detail_id, order_id, dish_id, quantity, price_at_time, notes, served_status) VALUES 
('DTL_001', 'ORD_1001', 'DISH_01', 1, 55000, 'Không ăn hành lá', TRUE),
('DTL_002', 'ORD_1001', 'DISH_04', 2, 25000, 'Ít đường, nhiều đá', TRUE);

-- 8. Invoice Test
INSERT INTO invoices (invoice_id, order_id, user_id, total_amount, discount_amount, final_amount, payment_method, payment_status) VALUES
('INV_2001', 'ORD_1001', 'USER_02', 105000, 5000, 100000, 'BANK_TRANSFER', 'PAID');

-- 9. Audit Logs Test
INSERT INTO audit_logs (log_id, user_id, action, table_name, description) VALUES
('LOG_001', 'USER_02', 'CREATE', 'orders', 'Tạo đơn hàng ORD_1001 cho TABLE_05'),
('LOG_002', 'USER_02', 'CREATE', 'invoices', 'Thanh toán hóa đơn INV_2001 thành công qua BANK_TRANSFER');