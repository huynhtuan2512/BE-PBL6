-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: restaurant_db
-- ------------------------------------------------------
-- Server version	9.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dishes`
--

DROP TABLE IF EXISTS `dishes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dishes` (
  `dish_id` varchar(50) NOT NULL,
  `dish_name` varchar(100) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `image_url` varchar(255) DEFAULT NULL,
  `ai_label_id` varchar(50) DEFAULT NULL,
  `is_available` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`dish_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dishes`
--

LOCK TABLES `dishes` WRITE;
/*!40000 ALTER TABLE `dishes` DISABLE KEYS */;
INSERT INTO `dishes` VALUES ('DISH_01','Phở Bò Đặc Biệt',55000.00,'https://example.com/pho.jpg','pho_bo',1),('DISH_02','Cơm Chiên Dương Châu',45000.00,'https://example.com/com.jpg','com_chien',1),('DISH_03','Mì Quảng Gà',50000.00,'https://example.com/mi.jpg','mi_quang',1),('DISH_04','Trà Đào Cam Sả',25000.00,'https://example.com/tradao.jpg','tra_dao',1);
/*!40000 ALTER TABLE `dishes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `nodes`
--

DROP TABLE IF EXISTS `nodes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nodes` (
  `qr_id` varchar(50) NOT NULL,
  `node_name` varchar(100) NOT NULL,
  `node_type` varchar(30) NOT NULL,
  `pos_x` int DEFAULT '0',
  `pos_y` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`qr_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `nodes`
--

LOCK TABLES `nodes` WRITE;
/*!40000 ALTER TABLE `nodes` DISABLE KEYS */;
INSERT INTO `nodes` VALUES ('QR_CROSS_01','Giao lộ 1','INTERSECTION',200,100,'2026-09-24 05:04:30'),('QR_CROSS_02','Giao lộ 2','INTERSECTION',300,100,'2026-09-24 05:04:30'),('QR_CROSS_03','Giao lộ 3','INTERSECTION',400,100,'2026-09-24 05:04:30'),('QR_HOME','Trạm Bếp','START',100,100,'2026-09-24 05:04:30'),('QR_TABLE_01','Bàn số 1','TABLE',200,50,'2026-09-24 05:04:30'),('QR_TABLE_02','Bàn số 2','TABLE',200,150,'2026-09-24 05:04:30'),('QR_TABLE_03','Bàn số 3','TABLE',300,50,'2026-09-24 05:04:30'),('QR_TABLE_04','Bàn số 4','TABLE',300,150,'2026-09-24 05:04:30'),('QR_TABLE_05','Bàn số 5','TABLE',400,50,'2026-09-24 05:04:30'),('QR_TABLE_06','Bàn số 6','TABLE',400,150,'2026-09-24 05:04:30');
/*!40000 ALTER TABLE `nodes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_details`
--

DROP TABLE IF EXISTS `order_details`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_details` (
  `detail_id` varchar(50) NOT NULL,
  `order_id` varchar(50) NOT NULL,
  `dish_id` varchar(50) NOT NULL,
  `quantity` int DEFAULT '1',
  `served_status` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`detail_id`),
  KEY `order_id` (`order_id`),
  KEY `dish_id` (`dish_id`),
  CONSTRAINT `order_details_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `order_details_ibfk_2` FOREIGN KEY (`dish_id`) REFERENCES `dishes` (`dish_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_details`
--

LOCK TABLES `order_details` WRITE;
/*!40000 ALTER TABLE `order_details` DISABLE KEYS */;
INSERT INTO `order_details` VALUES ('DTL_001','ORD_1001','DISH_01',1,1),('DTL_002','ORD_1001','DISH_04',2,1);
/*!40000 ALTER TABLE `order_details` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `order_id` varchar(50) NOT NULL,
  `table_id` varchar(50) NOT NULL,
  `created_by_user_id` varchar(50) DEFAULT NULL,
  `total_amount` decimal(10,2) DEFAULT '0.00',
  `order_status` varchar(30) DEFAULT 'PENDING',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`order_id`),
  KEY `table_id` (`table_id`),
  KEY `created_by_user_id` (`created_by_user_id`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`table_id`) REFERENCES `tables` (`table_id`),
  CONSTRAINT `orders_ibfk_2` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
INSERT INTO `orders` VALUES ('ORD_1001','TABLE_05','USER_02',105000.00,'DELIVERING','2026-09-24 05:04:30');
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `robot_status`
--

DROP TABLE IF EXISTS `robot_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `robot_status` (
  `id` varchar(50) NOT NULL,
  `current_qr_id` varchar(50) DEFAULT NULL,
  `current_order_id` varchar(50) DEFAULT NULL,
  `robot_state` varchar(30) DEFAULT 'IDLE',
  `obstacle_detected` tinyint(1) DEFAULT '0',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `current_qr_id` (`current_qr_id`),
  KEY `current_order_id` (`current_order_id`),
  CONSTRAINT `robot_status_ibfk_1` FOREIGN KEY (`current_qr_id`) REFERENCES `nodes` (`qr_id`),
  CONSTRAINT `robot_status_ibfk_2` FOREIGN KEY (`current_order_id`) REFERENCES `orders` (`order_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `robot_status`
--

LOCK TABLES `robot_status` WRITE;
/*!40000 ALTER TABLE `robot_status` DISABLE KEYS */;
INSERT INTO `robot_status` VALUES ('ROBOT_01','QR_HOME','ORD_1001','DELIVERING',0,'2026-09-24 05:04:30');
/*!40000 ALTER TABLE `robot_status` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `robot_travel_logs`
--

DROP TABLE IF EXISTS `robot_travel_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `robot_travel_logs` (
  `log_id` varchar(50) NOT NULL,
  `order_id` varchar(50) NOT NULL,
  `qr_id` varchar(50) NOT NULL,
  `action_taken` varchar(30) NOT NULL,
  `step_order` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `order_id` (`order_id`),
  KEY `qr_id` (`qr_id`),
  CONSTRAINT `robot_travel_logs_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `robot_travel_logs_ibfk_2` FOREIGN KEY (`qr_id`) REFERENCES `nodes` (`qr_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `robot_travel_logs`
--

LOCK TABLES `robot_travel_logs` WRITE;
/*!40000 ALTER TABLE `robot_travel_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `robot_travel_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `role_id` varchar(50) NOT NULL,
  `role_name` varchar(30) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES ('ROLE_01','ADMIN','Quản trị viên hệ thống'),('ROLE_02','STAFF','Nhân viên phục vụ'),('ROLE_03','CUSTOMER','Khách hàng tại bàn');
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `routings`
--

DROP TABLE IF EXISTS `routings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `routings` (
  `id` varchar(50) NOT NULL,
  `qr_id` varchar(50) NOT NULL,
  `target_table_id` varchar(50) DEFAULT NULL,
  `action` varchar(30) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `qr_id` (`qr_id`),
  KEY `target_table_id` (`target_table_id`),
  CONSTRAINT `routings_ibfk_1` FOREIGN KEY (`qr_id`) REFERENCES `nodes` (`qr_id`) ON DELETE CASCADE,
  CONSTRAINT `routings_ibfk_2` FOREIGN KEY (`target_table_id`) REFERENCES `nodes` (`qr_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `routings`
--

LOCK TABLES `routings` WRITE;
/*!40000 ALTER TABLE `routings` DISABLE KEYS */;
INSERT INTO `routings` VALUES ('ROUTE_01','QR_CROSS_01','QR_TABLE_01','TURN_LEFT','Rẽ trái để vào Bàn 1'),('ROUTE_02','QR_CROSS_01','QR_TABLE_02','TURN_RIGHT','Rẽ phải để vào Bàn 2'),('ROUTE_03','QR_CROSS_01',NULL,'GO_STRAIGHT','Đi thẳng tới các giao lộ tiếp theo'),('ROUTE_04','QR_CROSS_02','QR_TABLE_03','TURN_LEFT','Rẽ trái để vào Bàn 3'),('ROUTE_05','QR_CROSS_02','QR_TABLE_04','TURN_RIGHT','Rẽ phải để vào Bàn 4'),('ROUTE_06','QR_CROSS_02',NULL,'GO_STRAIGHT','Đi thẳng tới giao lộ 3'),('ROUTE_07','QR_CROSS_03','QR_TABLE_05','TURN_LEFT','Rẽ trái để vào Bàn 5'),('ROUTE_08','QR_CROSS_03','QR_TABLE_06','TURN_RIGHT','Rẽ phải để vào Bàn 6');
/*!40000 ALTER TABLE `routings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tables`
--

DROP TABLE IF EXISTS `tables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tables` (
  `table_id` varchar(50) NOT NULL,
  `table_number` int NOT NULL,
  `qr_id` varchar(50) NOT NULL,
  `status` varchar(20) DEFAULT 'EMPTY',
  PRIMARY KEY (`table_id`),
  KEY `qr_id` (`qr_id`),
  CONSTRAINT `tables_ibfk_1` FOREIGN KEY (`qr_id`) REFERENCES `nodes` (`qr_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tables`
--

LOCK TABLES `tables` WRITE;
/*!40000 ALTER TABLE `tables` DISABLE KEYS */;
INSERT INTO `tables` VALUES ('TABLE_01',1,'QR_TABLE_01','EMPTY'),('TABLE_02',2,'QR_TABLE_02','EMPTY'),('TABLE_03',3,'QR_TABLE_03','EMPTY'),('TABLE_04',4,'QR_TABLE_04','EMPTY'),('TABLE_05',5,'QR_TABLE_05','EMPTY'),('TABLE_06',6,'QR_TABLE_06','EMPTY');
/*!40000 ALTER TABLE `tables` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` varchar(50) NOT NULL,
  `role_id` varchar(50) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(100) NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES ('USER_01','ROLE_01','admin','hash_admin_123','Nguyễn Văn Admin','0905123456',1,'2026-09-24 05:04:30'),('USER_02','ROLE_02','staff01','hash_staff_123','Trần Thị Nhân Viên','0905654321',1,'2026-09-24 05:04:30');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-24 12:06:20
