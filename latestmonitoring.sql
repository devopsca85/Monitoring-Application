-- MySQL dump 10.13  Distrib 8.0.45, for Linux (x86_64)
--
-- Host: localhost    Database: monitoring_db
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alerts`
--

DROP TABLE IF EXISTS `alerts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alerts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `site_id` int DEFAULT NULL,
  `alert_type` enum('OK','WARNING','CRITICAL') DEFAULT NULL,
  `message` text,
  `notified` tinyint(1) DEFAULT NULL,
  `notified_at` datetime DEFAULT NULL,
  `resolved` tinyint(1) DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_alerts_site_id` (`site_id`),
  CONSTRAINT `alerts_ibfk_1` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alerts`
--

LOCK TABLES `alerts` WRITE;
/*!40000 ALTER TABLE `alerts` DISABLE KEYS */;
INSERT INTO `alerts` VALUES (1,1,'CRITICAL','Login succeeded but success indicator not found',0,NULL,1,'2026-04-09 18:13:02','2026-04-09 15:04:59'),(2,NULL,'CRITICAL','HTTP 404 error on ehsqa4.fldata.com (https://ehsqa4.fldata.com). HTTP 404 Not Found',0,NULL,1,'2026-04-09 16:17:48','2026-04-09 16:12:47'),(3,NULL,'CRITICAL','HTTP 404 error on ehsqa4.fldata.com (https://ehsqa4.fldata.com). HTTP 404 Not Found',0,NULL,1,'2026-04-09 16:40:02','2026-04-09 16:36:19'),(4,NULL,'CRITICAL','HTTP 404 error on ehsqa01.fldata.com (https://ehsqa01.fldata.com). HTTP 404 Not Found',0,NULL,1,'2026-04-09 16:40:05','2026-04-09 16:37:48'),(5,NULL,'CRITICAL','HTTP 404 error on ehsqa01.fldata.com (https://ehsqa01.fldata.com). HTTP 404 Not Found',0,NULL,1,'2026-04-09 17:25:04','2026-04-09 17:14:21'),(6,NULL,'CRITICAL','HTTP 404 error on ehsqa01.fldata.com (https://ehsqa01.fldata.com). HTTP 404 Not Found',0,NULL,1,'2026-04-09 17:34:51','2026-04-09 17:29:50'),(7,1,'CRITICAL','Login failed — error on page: The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas',0,NULL,1,'2026-04-09 18:23:02','2026-04-09 18:17:23'),(8,NULL,'CRITICAL','Page.goto: net::ERR_NAME_NOT_RESOLVED at http://test.com/\nCall log:\nnavigating to \"http://test.com/\", waiting until \"domcontentloaded\"\n',0,NULL,0,NULL,'2026-04-09 18:59:03'),(9,NULL,'CRITICAL','Page.goto: net::ERR_CERT_COMMON_NAME_INVALID at https://eshqa1.fldata.com/\nCall log:\nnavigating to \"https://eshqa1.fldata.com/\", waiting until \"domcontentloaded\"\n',0,NULL,0,NULL,'2026-04-09 19:01:03'),(10,NULL,'CRITICAL','Page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL\nCall log:\nnavigating to \"ehsqa3.fldata.com/qazwsx1945.aspx\", waiting until \"domcontentloaded\"\n',0,NULL,1,'2026-04-09 19:11:30','2026-04-09 19:07:48'),(11,1,'CRITICAL','Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas',0,NULL,1,'2026-04-09 19:51:38','2026-04-09 19:42:24'),(12,NULL,'CRITICAL','Login failed — expected \'mainpage.aspx\' in URL but got: https://ehsqa3.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Cant%20login%20sorry!!',0,NULL,0,NULL,'2026-04-09 19:42:25'),(13,11,'CRITICAL','Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas',0,NULL,1,'2026-04-09 20:06:07','2026-04-09 20:02:29'),(14,1,'CRITICAL','Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas',1,'2026-04-09 20:10:58',1,'2026-04-09 20:19:05','2026-04-09 20:10:57');
/*!40000 ALTER TABLE `alerts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `monitoring_results`
--

DROP TABLE IF EXISTS `monitoring_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitoring_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `site_id` int DEFAULT NULL,
  `check_type` enum('UPTIME','LOGIN','MULTI_PAGE') DEFAULT NULL,
  `status` enum('OK','WARNING','CRITICAL') DEFAULT NULL,
  `response_time_ms` float DEFAULT NULL,
  `status_code` int DEFAULT NULL,
  `error_message` text,
  `screenshot_url` varchar(500) DEFAULT NULL,
  `details` text,
  `checked_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_monitoring_results_site_id` (`site_id`),
  KEY `ix_monitoring_results_checked_at` (`checked_at`),
  CONSTRAINT `monitoring_results_ibfk_1` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=305 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `monitoring_results`
--

LOCK TABLES `monitoring_results` WRITE;
/*!40000 ALTER TABLE `monitoring_results` DISABLE KEYS */;
INSERT INTO `monitoring_results` VALUES (1,1,'LOGIN','CRITICAL',23138,200,'Login succeeded but success indicator not found','','','2026-04-09 14:55:10'),(2,1,'LOGIN','CRITICAL',12146.2,200,'Login succeeded but success indicator not found','','','2026-04-09 14:59:59'),(3,1,'LOGIN','CRITICAL',11879.5,200,'Login succeeded but success indicator not found','','','2026-04-09 15:04:59'),(4,1,'LOGIN','CRITICAL',11860,200,'Login succeeded but success indicator not found','','','2026-04-09 15:09:59'),(5,1,'LOGIN','CRITICAL',12172.7,200,'Login succeeded but success indicator not found','','','2026-04-09 15:15:00'),(6,1,'LOGIN','CRITICAL',12226.2,200,'Login succeeded but success indicator not found','','','2026-04-09 15:15:59'),(7,1,'LOGIN','CRITICAL',11916.6,200,'Login succeeded but success indicator not found','','','2026-04-09 15:20:58'),(8,NULL,'UPTIME','OK',964.097,200,'','','','2026-04-09 15:22:17'),(9,1,'LOGIN','CRITICAL',11971.8,200,'Login succeeded but success indicator not found','','','2026-04-09 15:25:58'),(10,NULL,'UPTIME','OK',972.15,200,'','','','2026-04-09 15:27:17'),(11,1,'LOGIN','CRITICAL',12010.2,200,'Login succeeded but success indicator not found','','','2026-04-09 15:30:58'),(12,NULL,'UPTIME','OK',993.54,200,'','','','2026-04-09 15:32:17'),(13,NULL,'UPTIME','OK',1582.88,200,'','','','2026-04-09 15:33:20'),(14,1,'LOGIN','CRITICAL',12709.8,200,'Login succeeded but success indicator not found','','','2026-04-09 15:33:31'),(15,NULL,'UPTIME','OK',1568.37,200,'','','','2026-04-09 15:37:00'),(16,1,'LOGIN','CRITICAL',12713.1,200,'Login succeeded but success indicator not found','','','2026-04-09 15:37:11'),(17,NULL,'UPTIME','OK',1298.5,200,'','','','2026-04-09 15:42:00'),(18,1,'LOGIN','CRITICAL',12437.2,200,'Login succeeded but success indicator not found','','','2026-04-09 15:42:11'),(19,NULL,'UPTIME','OK',1258.53,200,'','','','2026-04-09 15:47:00'),(20,1,'LOGIN','CRITICAL',12686.1,200,'Login succeeded but success indicator not found','','','2026-04-09 15:47:11'),(21,NULL,'UPTIME','OK',1556.39,200,'','','','2026-04-09 15:50:07'),(22,1,'LOGIN','CRITICAL',12666.4,200,'Login succeeded but success indicator not found','','','2026-04-09 15:50:18'),(23,NULL,'UPTIME','CRITICAL',897.905,404,'HTTP 404','','','2026-04-09 15:55:06'),(24,1,'LOGIN','CRITICAL',30937.3,0,'Page.fill: Timeout 30000ms exceeded.\nCall log:\nwaiting for locator(\"#USERID\")\n','','','2026-04-09 15:55:36'),(25,1,'LOGIN','CRITICAL',19321.4,200,'Login succeeded but success indicator not found','','','2026-04-09 15:58:17'),(26,NULL,'UPTIME','OK',810.434,200,'','','','2026-04-09 15:58:39'),(27,1,'LOGIN','CRITICAL',12612.6,200,'Login succeeded but success indicator not found','','','2026-04-09 15:59:18'),(28,NULL,'UPTIME','OK',1254.5,200,'','','','2026-04-09 16:00:06'),(29,1,'LOGIN','CRITICAL',12569.9,200,'Login succeeded but success indicator not found','','','2026-04-09 16:00:18'),(30,1,'LOGIN','CRITICAL',12173.5,200,'Login succeeded but success indicator not found','','','2026-04-09 16:01:45'),(31,NULL,'UPTIME','CRITICAL',630.668,404,'HTTP 404','','','2026-04-09 16:04:23'),(32,NULL,'UPTIME','CRITICAL',940.032,404,'HTTP 404','','','2026-04-09 16:05:06'),(33,1,'LOGIN','CRITICAL',31027.5,0,'Page.fill: Timeout 30000ms exceeded.\nCall log:\nwaiting for locator(\"#USERID\")\n','','','2026-04-09 16:05:36'),(34,NULL,'UPTIME','OK',16690.5,200,'','','','2026-04-09 16:08:02'),(35,1,'LOGIN','CRITICAL',31629.7,200,'Login succeeded but success indicator not found','','','2026-04-09 16:08:17'),(36,NULL,'UPTIME','CRITICAL',948.886,404,'HTTP 404 Not Found','','','2026-04-09 16:12:47'),(37,1,'LOGIN','CRITICAL',30826.3,0,'Page.fill: Timeout 30000ms exceeded.\nCall log:\nwaiting for locator(\"#USERID\")\n','','','2026-04-09 16:13:16'),(38,1,'LOGIN','CRITICAL',30653.3,0,'Page.fill: Timeout 30000ms exceeded.\nCall log:\nwaiting for locator(\"#USERID\")\n','','','2026-04-09 16:13:37'),(39,1,'LOGIN','CRITICAL',18347.5,200,'Login succeeded but success indicator not found','','','2026-04-09 16:15:59'),(40,NULL,'UPTIME','OK',1426.37,200,'','','','2026-04-09 16:17:47'),(41,1,'LOGIN','CRITICAL',14117.8,200,'Login succeeded but success indicator not found','','','2026-04-09 16:18:00'),(42,1,'LOGIN','CRITICAL',4006.35,200,'Login succeeded but success indicator not found','','','2026-04-09 16:22:16'),(43,NULL,'UPTIME','OK',1204.31,200,'','','','2026-04-09 16:22:47'),(44,1,'LOGIN','CRITICAL',2437.26,200,'Login succeeded but success indicator not found','','','2026-04-09 16:22:48'),(45,NULL,'UPTIME','OK',1601.39,200,'','','','2026-04-09 16:26:19'),(46,1,'LOGIN','CRITICAL',36576,200,'Login succeeded but success indicator \'#.ajax__tab_panel[style*=\"visible\"] table\' not found on page','','','2026-04-09 16:26:54'),(47,NULL,'UPTIME','OK',913.074,200,'','','','2026-04-09 16:27:48'),(48,1,'LOGIN','CRITICAL',33971.2,200,'Login succeeded but success indicator \'#.ajax__tab_panel[style*=\"visible\"] table\' not found on page','','','2026-04-09 16:29:59'),(49,NULL,'UPTIME','OK',1549.58,200,'','','','2026-04-09 16:31:19'),(50,1,'LOGIN','CRITICAL',49731.4,200,'Login succeeded but success indicator \'.ajax__tab_panel[style*=\"visible\"] table\' not found on page','','','2026-04-09 16:31:28'),(51,1,'LOGIN','CRITICAL',50537.4,200,'Login succeeded but success indicator \'.ajax__tab_panel[style*=\"visible\"] table\' not found on page','','','2026-04-09 16:32:08'),(52,1,'LOGIN','CRITICAL',49228.2,200,'Login succeeded but success indicator \'.ajax__tab_panel[style*=\"visible\"] table\' not found on page','','','2026-04-09 16:32:25'),(53,NULL,'UPTIME','OK',877.67,200,'','','','2026-04-09 16:32:48'),(54,1,'LOGIN','CRITICAL',460.701,0,'\'login_url\'','','','2026-04-09 16:33:24'),(55,NULL,'UPTIME','OK',970.553,200,'','','','2026-04-09 16:33:25'),(56,NULL,'UPTIME','OK',856.495,200,'','','','2026-04-09 16:33:26'),(57,1,'LOGIN','CRITICAL',484.998,0,'\'login_url\'','','','2026-04-09 16:35:38'),(58,NULL,'UPTIME','OK',971.242,200,'','','','2026-04-09 16:35:39'),(59,NULL,'UPTIME','OK',847.518,200,'','','','2026-04-09 16:35:40'),(60,NULL,'UPTIME','CRITICAL',877.689,404,'HTTP 404 Not Found','','','2026-04-09 16:36:19'),(61,1,'LOGIN','CRITICAL',31015.9,0,'Page.fill: Timeout 30000ms exceeded.\nCall log:\nwaiting for locator(\"#USERID\")\n','','','2026-04-09 16:36:49'),(62,NULL,'UPTIME','CRITICAL',617.117,404,'HTTP 404 Not Found','','','2026-04-09 16:37:48'),(63,1,'LOGIN','CRITICAL',490.269,0,'\'login_url\'','','','2026-04-09 16:40:00'),(64,NULL,'UPTIME','OK',1034.05,200,'','','','2026-04-09 16:40:01'),(65,NULL,'UPTIME','OK',2235.79,200,'','','','2026-04-09 16:40:04'),(66,NULL,'UPTIME','OK',1310.94,200,'','','','2026-04-09 16:41:19'),(67,1,'LOGIN','CRITICAL',53111.9,200,'Login succeeded but success indicator \'.ajax__tab_panel[style*=\"visible\"] table\' not found on page','','','2026-04-09 16:42:11'),(68,NULL,'UPTIME','OK',844.573,200,'','','','2026-04-09 16:42:48'),(69,1,'LOGIN','CRITICAL',482.719,0,'\'login_url\'','','','2026-04-09 16:45:00'),(70,NULL,'UPTIME','OK',1026.78,200,'','','','2026-04-09 16:45:01'),(71,NULL,'UPTIME','OK',859.735,200,'','','','2026-04-09 16:45:02'),(72,NULL,'UPTIME','OK',1333.08,200,'','','','2026-04-09 16:46:19'),(73,1,'LOGIN','CRITICAL',49407.9,200,'Login succeeded but success indicator \'table#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 16:47:07'),(74,NULL,'UPTIME','OK',934.737,200,'','','','2026-04-09 16:47:48'),(75,1,'LOGIN','CRITICAL',499.269,0,'\'login_url\'','','','2026-04-09 16:50:00'),(76,NULL,'UPTIME','OK',1018.03,200,'','','','2026-04-09 16:50:01'),(77,NULL,'UPTIME','OK',847.884,200,'','','','2026-04-09 16:50:02'),(78,NULL,'UPTIME','OK',1301.52,200,'','','','2026-04-09 16:51:19'),(79,1,'LOGIN','CRITICAL',49246.9,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 16:52:07'),(80,NULL,'UPTIME','OK',851.883,200,'','','','2026-04-09 16:52:48'),(81,1,'LOGIN','CRITICAL',496.34,0,'\'login_url\'','','','2026-04-09 16:55:00'),(82,NULL,'UPTIME','OK',900.85,200,'','','','2026-04-09 16:55:01'),(83,NULL,'UPTIME','OK',942.432,200,'','','','2026-04-09 16:55:02'),(84,NULL,'UPTIME','OK',1155.19,200,'','','','2026-04-09 16:56:19'),(85,1,'LOGIN','CRITICAL',49467.9,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 16:57:07'),(86,NULL,'UPTIME','OK',830.997,200,'','','','2026-04-09 16:57:48'),(87,NULL,'UPTIME','OK',1949.5,200,'','','','2026-04-09 16:59:22'),(88,NULL,'UPTIME','OK',2199.98,200,'','','','2026-04-09 16:59:22'),(89,1,'LOGIN','CRITICAL',655.728,0,'\'login_url\'','','','2026-04-09 17:00:00'),(90,NULL,'UPTIME','OK',1013.02,200,'','','','2026-04-09 17:00:01'),(91,NULL,'UPTIME','OK',865.767,200,'','','','2026-04-09 17:00:02'),(92,1,'LOGIN','CRITICAL',50117.6,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 17:00:10'),(93,NULL,'UPTIME','OK',1583.07,200,'','','','2026-04-09 17:04:21'),(94,NULL,'UPTIME','OK',1674.27,200,'','','','2026-04-09 17:04:21'),(95,1,'LOGIN','CRITICAL',489.06,0,'\'login_url\'','','','2026-04-09 17:05:00'),(96,NULL,'UPTIME','OK',984.117,200,'','','','2026-04-09 17:05:01'),(97,NULL,'UPTIME','OK',899.902,200,'','','','2026-04-09 17:05:02'),(98,1,'LOGIN','CRITICAL',49729.9,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 17:05:09'),(99,NULL,'UPTIME','OK',1704.18,200,'','','','2026-04-09 17:09:21'),(100,NULL,'UPTIME','OK',1901.23,200,'','','','2026-04-09 17:09:21'),(101,1,'LOGIN','CRITICAL',535.105,0,'\'login_url\'','','','2026-04-09 17:10:00'),(102,NULL,'UPTIME','OK',1036.72,200,'','','','2026-04-09 17:10:01'),(103,NULL,'UPTIME','OK',967.888,200,'','','','2026-04-09 17:10:02'),(104,1,'LOGIN','CRITICAL',50723,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 17:10:10'),(105,NULL,'UPTIME','CRITICAL',1269.26,404,'HTTP 404 Not Found','','','2026-04-09 17:14:21'),(106,NULL,'UPTIME','OK',1833.36,200,'','','','2026-04-09 17:14:22'),(107,1,'LOGIN','CRITICAL',502.029,0,'\'login_url\'','','','2026-04-09 17:15:00'),(108,NULL,'UPTIME','OK',893.701,200,'','','','2026-04-09 17:15:01'),(109,NULL,'UPTIME','CRITICAL',609.982,404,'HTTP 404 Not Found','','','2026-04-09 17:15:02'),(110,1,'LOGIN','CRITICAL',50075.1,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 17:15:10'),(111,NULL,'UPTIME','CRITICAL',1277.11,404,'HTTP 404 Not Found','','','2026-04-09 17:19:21'),(112,NULL,'UPTIME','OK',1585.55,200,'','','','2026-04-09 17:19:21'),(113,1,'LOGIN','CRITICAL',505.639,0,'\'login_url\'','','','2026-04-09 17:20:00'),(114,NULL,'UPTIME','OK',955.966,200,'','','','2026-04-09 17:20:01'),(115,NULL,'UPTIME','CRITICAL',587.262,404,'HTTP 404 Not Found','','','2026-04-09 17:20:02'),(116,NULL,'UPTIME','CRITICAL',1461.72,404,'HTTP 404 Not Found','','','2026-04-09 17:20:40'),(117,NULL,'UPTIME','OK',1898.02,200,'','','','2026-04-09 17:20:41'),(118,1,'LOGIN','CRITICAL',50768.3,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 17:21:30'),(119,1,'LOGIN','CRITICAL',470.942,0,'\'login_url\'','','','2026-04-09 17:25:00'),(120,NULL,'UPTIME','OK',974.487,200,'','','','2026-04-09 17:25:01'),(121,NULL,'UPTIME','OK',2150.19,200,'','','','2026-04-09 17:25:03'),(122,NULL,'UPTIME','OK',1524,200,'','','','2026-04-09 17:25:41'),(123,NULL,'UPTIME','OK',1761.92,200,'','','','2026-04-09 17:25:41'),(124,1,'LOGIN','CRITICAL',49811.7,200,'Login succeeded but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found on page','','','2026-04-09 17:26:29'),(125,NULL,'UPTIME','CRITICAL',1542.17,404,'HTTP 404 Not Found','','','2026-04-09 17:29:50'),(126,NULL,'UPTIME','OK',2088.06,200,'','','','2026-04-09 17:29:50'),(127,1,'LOGIN','CRITICAL',500.648,0,'\'login_url\'','','','2026-04-09 17:30:00'),(128,NULL,'UPTIME','OK',939.518,200,'','','','2026-04-09 17:30:01'),(129,NULL,'UPTIME','CRITICAL',605.479,404,'HTTP 404 Not Found','','','2026-04-09 17:30:02'),(130,1,'LOGIN','CRITICAL',76850.6,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:31:05'),(131,NULL,'UPTIME','OK',1643.23,200,'','','','2026-04-09 17:34:50'),(132,NULL,'UPTIME','OK',2683.75,200,'','','','2026-04-09 17:34:51'),(133,1,'LOGIN','CRITICAL',76832.6,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:36:05'),(134,NULL,'UPTIME','OK',1428.97,200,'','','','2026-04-09 17:39:50'),(135,NULL,'UPTIME','OK',1770.28,200,'','','','2026-04-09 17:39:50'),(136,1,'LOGIN','CRITICAL',79024.1,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:41:07'),(137,NULL,'UPTIME','OK',1965.08,200,'','','','2026-04-09 17:41:45'),(138,NULL,'UPTIME','OK',2074.68,200,'','','','2026-04-09 17:41:46'),(139,1,'LOGIN','CRITICAL',16548.4,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:42:00'),(140,1,'LOGIN','CRITICAL',15367.9,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:43:35'),(141,1,'LOGIN','CRITICAL',15567.2,200,'Login completed but success indicator \'#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:46:05'),(142,NULL,'UPTIME','OK',1484.17,200,'','','','2026-04-09 17:46:45'),(143,NULL,'UPTIME','OK',1716.43,200,'','','','2026-04-09 17:46:45'),(144,1,'LOGIN','CRITICAL',15814.1,200,'Login completed but success indicator \'#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:46:59'),(145,1,'LOGIN','CRITICAL',11658.7,200,'Login completed but success indicator \'#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Other','','','2026-04-09 17:47:49'),(146,1,'LOGIN','CRITICAL',11693.3,200,'Login completed but success indicator \'#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Other','','','2026-04-09 17:49:11'),(147,NULL,'UPTIME','OK',1678.47,200,'','','','2026-04-09 17:51:45'),(148,NULL,'UPTIME','OK',1761.58,200,'','','','2026-04-09 17:51:45'),(149,1,'LOGIN','CRITICAL',12572.6,200,'Login completed but success indicator \'#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Other','','','2026-04-09 17:51:56'),(150,NULL,'UPTIME','OK',1982.04,200,'','','','2026-04-09 17:55:21'),(151,NULL,'UPTIME','OK',2242.61,200,'','','','2026-04-09 17:55:21'),(152,1,'LOGIN','CRITICAL',13021.3,200,'Login failed — page contains \'incorrect\'','','','2026-04-09 17:55:32'),(153,1,'LOGIN','CRITICAL',15161.9,200,'Login completed but success indicator \'#TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 17:58:12'),(154,NULL,'UPTIME','OK',1456.92,200,'','','','2026-04-09 18:00:21'),(155,NULL,'UPTIME','OK',1727.96,200,'','','','2026-04-09 18:00:21'),(156,1,'LOGIN','CRITICAL',14937.3,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 18:00:22'),(157,1,'LOGIN','CRITICAL',16133.3,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 18:00:35'),(158,NULL,'UPTIME','OK',1694.48,200,'','','','2026-04-09 18:05:21'),(159,NULL,'UPTIME','OK',1787.91,200,'','','','2026-04-09 18:05:21'),(160,1,'LOGIN','CRITICAL',15969,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 18:05:35'),(161,NULL,'UPTIME','OK',1527.39,200,'','','','2026-04-09 18:10:21'),(162,NULL,'UPTIME','OK',1553.05,200,'','','','2026-04-09 18:10:21'),(163,1,'LOGIN','CRITICAL',15675.6,200,'Login completed but success indicator \'TabContainer1_tbTrainingItems_gvTraining.table.table-striped\' not found. Current page: https://ehsqa4.fldata.com/mainpage.aspx','','','2026-04-09 18:10:35'),(164,NULL,'UPTIME','OK',1825.91,200,'','','','2026-04-09 18:12:17'),(165,NULL,'UPTIME','OK',2074.96,200,'','','','2026-04-09 18:12:17'),(166,1,'LOGIN','OK',46232.5,200,'','','','2026-04-09 18:13:01'),(167,NULL,'UPTIME','OK',1719.42,200,'','','','2026-04-09 18:17:17'),(168,NULL,'UPTIME','OK',1720.88,200,'','','','2026-04-09 18:17:17'),(169,1,'LOGIN','CRITICAL',7533.19,200,'Login failed — error on page: The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 18:17:23'),(170,1,'LOGIN','CRITICAL',6815.44,200,'Login failed — error on page: The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 18:17:32'),(171,NULL,'UPTIME','OK',1783.36,200,'','','','2026-04-09 18:22:17'),(172,NULL,'UPTIME','OK',1793.82,200,'','','','2026-04-09 18:22:17'),(173,1,'LOGIN','OK',46133.8,200,'','','','2026-04-09 18:23:01'),(174,NULL,'UPTIME','OK',1849.89,200,'','','','2026-04-09 18:26:14'),(175,NULL,'UPTIME','OK',2040.73,200,'','','','2026-04-09 18:26:14'),(176,1,'LOGIN','OK',48200.1,200,'','','','2026-04-09 18:27:00'),(177,NULL,'UPTIME','OK',797.274,200,'','','','2026-04-09 18:29:28'),(178,1,'LOGIN','OK',45888.8,200,'','','','2026-04-09 18:29:58'),(179,NULL,'UPTIME','OK',966.191,200,'','','','2026-04-09 18:31:13'),(180,NULL,'UPTIME','OK',1943.35,200,'','','','2026-04-09 18:32:53'),(181,NULL,'UPTIME','OK',1969.24,200,'','','','2026-04-09 18:32:53'),(182,1,'LOGIN','OK',45999.8,200,'','','','2026-04-09 18:33:37'),(183,NULL,'UPTIME','OK',1208.74,200,'','','','2026-04-09 18:35:52'),(184,1,'LOGIN','OK',45209.4,200,'','','','2026-04-09 18:36:36'),(185,NULL,'UPTIME','OK',1033.37,200,'','','','2026-04-09 18:38:52'),(186,NULL,'LOGIN','OK',6655.79,200,'','','','2026-04-09 18:39:28'),(187,1,'LOGIN','OK',45050.5,200,'','','','2026-04-09 18:39:36'),(188,NULL,'UPTIME','OK',1131.32,200,'','','','2026-04-09 18:41:52'),(189,NULL,'LOGIN','OK',6670.96,200,'','','','2026-04-09 18:42:28'),(190,1,'LOGIN','OK',45619.6,200,'','','','2026-04-09 18:42:37'),(191,NULL,'UPTIME','OK',1201.17,200,'','','','2026-04-09 18:44:52'),(192,NULL,'LOGIN','OK',6676.53,200,'','','','2026-04-09 18:45:28'),(193,NULL,'LOGIN','OK',6490.77,200,'','','','2026-04-09 18:45:30'),(194,1,'LOGIN','OK',45933.1,200,'','','','2026-04-09 18:45:37'),(195,NULL,'UPTIME','OK',1149.48,200,'','','','2026-04-09 18:47:52'),(196,NULL,'LOGIN','OK',6550.51,200,'','','','2026-04-09 18:48:28'),(197,1,'LOGIN','OK',45356.8,200,'','','','2026-04-09 18:48:36'),(198,NULL,'UPTIME','OK',1185.15,200,'','','','2026-04-09 18:50:52'),(199,NULL,'LOGIN','OK',6650.53,200,'','','','2026-04-09 18:51:28'),(200,1,'LOGIN','OK',45713.1,200,'','','','2026-04-09 18:51:37'),(201,NULL,'UPTIME','OK',1313.9,200,'','','','2026-04-09 18:53:52'),(202,NULL,'LOGIN','OK',6628.37,200,'','','','2026-04-09 18:54:28'),(203,NULL,'UPTIME','OK',1098.55,200,'','','','2026-04-09 18:55:04'),(204,NULL,'UPTIME','OK',851.144,200,'','','','2026-04-09 18:58:03'),(205,NULL,'UPTIME','CRITICAL',482.339,0,'Page.goto: net::ERR_NAME_NOT_RESOLVED at http://test.com/\nCall log:\nnavigating to \"http://test.com/\", waiting until \"domcontentloaded\"\n','','','2026-04-09 18:59:03'),(206,NULL,'UPTIME','CRITICAL',860.106,0,'Page.goto: net::ERR_CERT_COMMON_NAME_INVALID at https://eshqa1.fldata.com/\nCall log:\nnavigating to \"https://eshqa1.fldata.com/\", waiting until \"domcontentloaded\"\n','','','2026-04-09 19:01:03'),(207,NULL,'UPTIME','OK',1221.7,200,'','','','2026-04-09 19:01:04'),(208,NULL,'UPTIME','CRITICAL',480.014,0,'Page.goto: net::ERR_NAME_NOT_RESOLVED at http://test.com/\nCall log:\nnavigating to \"http://test.com/\", waiting until \"domcontentloaded\"\n','','','2026-04-09 19:02:03'),(209,NULL,'UPTIME','CRITICAL',1264.37,0,'Page.goto: net::ERR_CERT_COMMON_NAME_INVALID at https://eshqa1.fldata.com/\nCall log:\nnavigating to \"https://eshqa1.fldata.com/\", waiting until \"domcontentloaded\"\n','','','2026-04-09 19:04:04'),(210,NULL,'UPTIME','OK',1510.88,200,'','','','2026-04-09 19:04:04'),(211,1,'LOGIN','OK',47005.3,200,'','','','2026-04-09 19:04:50'),(212,NULL,'UPTIME','CRITICAL',507.599,0,'Page.goto: net::ERR_NAME_NOT_RESOLVED at http://test.com/\nCall log:\nnavigating to \"http://test.com/\", waiting until \"domcontentloaded\"\n','','','2026-04-09 19:05:03'),(213,NULL,'UPTIME','OK',1139.96,200,'','','','2026-04-09 19:07:04'),(214,NULL,'LOGIN','CRITICAL',459.503,0,'Page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL\nCall log:\nnavigating to \"ehsqa3.fldata.com/qazwsx1945.aspx\", waiting until \"domcontentloaded\"\n','','','2026-04-09 19:07:48'),(215,1,'LOGIN','OK',45764.3,200,'','','','2026-04-09 19:07:49'),(216,NULL,'UPTIME','OK',1104.62,200,'','','','2026-04-09 19:10:04'),(217,1,'LOGIN','OK',46170.7,200,'','','','2026-04-09 19:10:49'),(218,NULL,'LOGIN','OK',41177.6,200,'','','','2026-04-09 19:11:29'),(219,NULL,'UPTIME','OK',1151.64,200,'','','','2026-04-09 19:13:04'),(220,1,'LOGIN','OK',45905.3,200,'','','','2026-04-09 19:13:49'),(221,NULL,'LOGIN','OK',41294.5,200,'','','','2026-04-09 19:14:29'),(222,NULL,'UPTIME','OK',1161.62,200,'','','','2026-04-09 19:16:04'),(223,1,'LOGIN','OK',46168,200,'','','','2026-04-09 19:16:49'),(224,NULL,'LOGIN','OK',42157.8,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 299.15642738342285}]','2026-04-09 19:17:30'),(225,NULL,'UPTIME','OK',1159.77,200,'','','','2026-04-09 19:19:04'),(226,1,'LOGIN','OK',45671.8,200,'','','','2026-04-09 19:19:49'),(227,NULL,'LOGIN','OK',49396.9,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 8202.556133270264}]','2026-04-09 19:20:37'),(228,NULL,'UPTIME','OK',1830.11,200,'','','','2026-04-09 19:22:05'),(229,1,'LOGIN','OK',46738.5,200,'','','','2026-04-09 19:22:50'),(230,NULL,'LOGIN','OK',43632.4,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 1932.3878288269043}]','2026-04-09 19:23:32'),(231,NULL,'UPTIME','OK',1965.37,200,'','','','2026-04-09 19:25:02'),(232,NULL,'UPTIME','OK',1784.4,200,'','','','2026-04-09 19:26:00'),(233,NULL,'LOGIN','OK',42199.8,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 303.91454696655273}]','2026-04-09 19:26:40'),(234,1,'LOGIN','OK',46345.1,200,'','','','2026-04-09 19:26:44'),(235,NULL,'UPTIME','OK',1357.12,200,'','','','2026-04-09 19:28:59'),(236,NULL,'LOGIN','OK',41873.2,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 509.9458694458008}]','2026-04-09 19:29:40'),(237,1,'LOGIN','OK',46755.3,200,'','','','2026-04-09 19:29:45'),(238,NULL,'UPTIME','OK',1517.38,200,'','','','2026-04-09 19:32:00'),(239,NULL,'LOGIN','OK',43832.7,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 330.0778865814209}]','2026-04-09 19:32:42'),(240,1,'LOGIN','OK',46373.3,200,'','','','2026-04-09 19:32:44'),(241,NULL,'UPTIME','OK',1449.86,200,'','','','2026-04-09 19:35:00'),(242,NULL,'LOGIN','OK',42582.2,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 333.07480812072754}]','2026-04-09 19:35:41'),(243,1,'LOGIN','OK',47505,200,'','','','2026-04-09 19:35:46'),(244,NULL,'UPTIME','OK',1780.35,200,'','','','2026-04-09 19:36:18'),(245,NULL,'LOGIN','OK',43978.6,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 513.2358074188232}]','2026-04-09 19:37:00'),(246,1,'LOGIN','OK',47059.4,200,'','','','2026-04-09 19:37:03'),(247,NULL,'UPTIME','OK',1539.06,200,'','','','2026-04-09 19:39:17'),(248,NULL,'LOGIN','OK',42180.4,200,'','','[{\"page_name\": \"App Dashboard\", \"status\": \"ok\", \"error\": \"\", \"response_time_ms\": 344.77925300598145}]','2026-04-09 19:39:58'),(249,1,'LOGIN','OK',46184.1,200,'','','','2026-04-09 19:40:02'),(250,NULL,'UPTIME','OK',1529.14,200,'','','','2026-04-09 19:42:17'),(251,1,'LOGIN','CRITICAL',7810.63,200,'Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 19:42:24'),(252,NULL,'LOGIN','CRITICAL',8121.62,200,'Login failed — expected \'mainpage.aspx\' in URL but got: https://ehsqa3.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Cant%20login%20sorry!!','','','2026-04-09 19:42:25'),(253,NULL,'UPTIME','OK',1893.45,200,'','','','2026-04-09 19:44:53'),(254,NULL,'LOGIN','CRITICAL',8189.98,200,'Login failed — expected \'mainpage.aspx\' in URL but got: https://ehsqa3.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Cant%20login%20sorry!!','','','2026-04-09 19:45:00'),(255,1,'LOGIN','CRITICAL',8424.76,200,'Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 19:45:00'),(256,NULL,'UPTIME','OK',1751.54,200,'','','','2026-04-09 19:47:54'),(257,NULL,'LOGIN','CRITICAL',8340.28,200,'Login failed — expected \'mainpage.aspx\' in URL but got: https://ehsqa3.fldata.com/TMSRC5_LoginValidation.aspx?ErrorMessage=Cant%20login%20sorry!!','','','2026-04-09 19:48:00'),(258,1,'LOGIN','CRITICAL',8572.88,200,'Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 19:48:00'),(259,1,'LOGIN','OK',46616.1,200,'','','','2026-04-09 19:51:38'),(260,1,'LOGIN','OK',45647.6,200,'','','','2026-04-09 19:54:37'),(261,7,'LOGIN','OK',43461.1,200,'','','','2026-04-09 19:57:05'),(262,1,'LOGIN','OK',46641.1,200,'','','','2026-04-09 19:57:38'),(263,8,'LOGIN','OK',43671.8,200,'','','','2026-04-09 19:58:50'),(264,7,'LOGIN','OK',43591.1,200,'','','','2026-04-09 20:00:05'),(265,1,'LOGIN','OK',46806.5,200,'','','','2026-04-09 20:00:38'),(266,9,'LOGIN','OK',65925.2,200,'','','','2026-04-09 20:00:57'),(267,8,'LOGIN','OK',43298.2,200,'','','','2026-04-09 20:01:50'),(268,10,'LOGIN','OK',44168.9,200,'','','','2026-04-09 20:01:51'),(269,11,'LOGIN','CRITICAL',7697.16,200,'Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 20:02:29'),(270,7,'LOGIN','OK',45671.2,200,'','','','2026-04-09 20:03:07'),(271,9,'LOGIN','OK',50824.1,200,'','','','2026-04-09 20:03:42'),(272,8,'LOGIN','OK',42798.1,200,'','','','2026-04-09 20:04:49'),(273,10,'LOGIN','OK',44021,200,'','','','2026-04-09 20:04:51'),(274,7,'LOGIN','OK',44608.4,200,'','','','2026-04-09 20:06:06'),(275,11,'LOGIN','OK',44738.6,200,'','','','2026-04-09 20:06:06'),(276,9,'LOGIN','OK',63987.2,200,'','','','2026-04-09 20:06:55'),(277,11,'LOGIN','OK',45465.7,200,'','','','2026-04-09 20:09:04'),(278,8,'LOGIN','OK',47715.1,200,'','','','2026-04-09 20:09:06'),(279,7,'LOGIN','OK',47837,200,'','','','2026-04-09 20:09:06'),(280,10,'LOGIN','OK',47960.1,200,'','','','2026-04-09 20:09:07'),(281,1,'LOGIN','OK',49260.8,200,'','','','2026-04-09 20:09:08'),(282,9,'LOGIN','OK',67241,200,'','','','2026-04-09 20:09:26'),(283,1,'LOGIN','CRITICAL',7232.88,200,'Login failed — The user ID or password you entered is incorrect. Please try again, or contact your local Frontline administrator for assistance.\n\nNotes:\nPassword is case sensitive.\nIf you forgot your password, pleas','','','2026-04-09 20:10:57'),(284,11,'LOGIN','OK',44651.3,200,'','','','2026-04-09 20:12:03'),(285,10,'LOGIN','OK',44915.3,200,'','','','2026-04-09 20:12:03'),(286,7,'LOGIN','OK',47033.1,200,'','','','2026-04-09 20:12:05'),(287,8,'LOGIN','OK',60174.1,200,'','','','2026-04-09 20:12:18'),(288,9,'LOGIN','OK',62443.4,200,'','','','2026-04-09 20:12:21'),(289,11,'LOGIN','OK',43816.9,200,'','','','2026-04-09 20:15:02'),(290,8,'LOGIN','OK',44486.4,200,'','','','2026-04-09 20:15:03'),(291,7,'LOGIN','OK',44861,200,'','','','2026-04-09 20:15:03'),(292,10,'LOGIN','OK',45016.7,200,'','','','2026-04-09 20:15:03'),(293,9,'LOGIN','OK',52359.1,200,'','','','2026-04-09 20:15:11'),(294,11,'LOGIN','OK',43291.1,200,'','','','2026-04-09 20:18:02'),(295,8,'LOGIN','OK',45155.4,200,'','','','2026-04-09 20:18:03'),(296,10,'LOGIN','OK',46566.6,200,'','','','2026-04-09 20:18:05'),(297,7,'LOGIN','OK',46863.4,200,'','','','2026-04-09 20:18:05'),(298,9,'LOGIN','OK',63279.5,200,'','','','2026-04-09 20:18:22'),(299,1,'LOGIN','OK',46732.3,200,'','','','2026-04-09 20:19:04'),(300,7,'LOGIN','OK',46226.3,200,'','','','2026-04-09 20:21:05'),(301,10,'LOGIN','OK',46670.5,200,'','','','2026-04-09 20:21:05'),(302,11,'LOGIN','OK',47164.6,200,'','','','2026-04-09 20:21:06'),(303,8,'LOGIN','OK',49344.4,200,'','','','2026-04-09 20:21:08'),(304,9,'LOGIN','OK',52047.2,200,'','','','2026-04-09 20:21:10');
/*!40000 ALTER TABLE `monitoring_results` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `site_credentials`
--

DROP TABLE IF EXISTS `site_credentials`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `site_credentials` (
  `id` int NOT NULL AUTO_INCREMENT,
  `site_id` int DEFAULT NULL,
  `login_url` varchar(500) DEFAULT NULL,
  `username_selector` varchar(255) DEFAULT NULL,
  `password_selector` varchar(255) DEFAULT NULL,
  `submit_selector` varchar(255) DEFAULT NULL,
  `success_indicator` varchar(255) DEFAULT NULL,
  `expected_page` varchar(255) DEFAULT 'mainpage.aspx',
  `encrypted_username` text,
  `encrypted_password` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `site_id` (`site_id`),
  CONSTRAINT `site_credentials_ibfk_1` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `site_credentials`
--

LOCK TABLES `site_credentials` WRITE;
/*!40000 ALTER TABLE `site_credentials` DISABLE KEYS */;
INSERT INTO `site_credentials` VALUES (1,1,'https://ehsqa4.fldata.com','#USERID','#PASSWORD','#btnLogon','TabContainer1_tbTrainingItems_gvTraining.table.table-striped','mainpage.aspx','gAAAAABp2Alqf9D4kQwiQRhjYKwFBPOdHWmq8XercCI3af7VnG5sWd3Tm23Z9jpEOAG6FztyWNI2kH1UyZTHgenUjbD7bineLw==','gAAAAABp2AlqU__1ZiCGOX5szXKgCuNrL9LqjWB5VzOyWMlCo_l1Xdis8HgirZJJPcrDyYAf49CFXutiq38tHEOFToDjkuAMHA=='),(2,NULL,'https://ehsqa3.fldata.com/qazwsx1945.aspx','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp1_JWUJNQJax8KbHR7oQzAK7oRvChIVp4uvG4LHi175656STQPIbLNDx3HwoFLYhOD4cpSvO8Ny35WyIkUAQuJaqsOg==','gAAAAABp1_JWOOykizsmm5qnjRUA8mdxRguXsUsmpAppjGcOCM3G3qga9xaHOipUx-JunfZP9ZTMpn-6DWysv6pvseiYOQScpQ=='),(3,NULL,'https://ehsqa3.fldata.com/qazwsx1945.aspx','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp1_j3iVjHL7yPu-M2ZgAuZHvnBPHOigRkpbIQVN5Qw54QRBFZrLLjYObMYoCiBeHgTAMU39slP-HwOfvIA1VmRpQlQQ==','gAAAAABp2ACrIP43qSbNvt81E5zQZJsO1jPVvROCJWenwESr4_u4Xzr6CLAZgyYfpby5qmm4d9AsygytKNxqufVX2k3ibnO9hw=='),(4,7,'https://oxy.fldata.com/qazwsx1945.aspx','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp2ARkL0yP0VQ6Utd2tANvZehsETwa_-SORC4_bCwo7ySG4zPSkfmUoAjrm2Zvu5xq4F9JL558Byr2KGFMntgTZZtgYg==','gAAAAABp2ARkSMsTUrsD7JoN_HJry0KW2mA6Xr37oJmgPV_p7M8mO8VKY9ndQu7xzlIsXu-7s3l_iNuOigDcuZ0V1sd73-gW0g=='),(5,8,'https://totalenergies.fldata.com/qazwsx1945.aspx','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp2ATGWm5GV2poxZDmgC0DNaPv6lzD6f5Q2ODR5qyXC3RkQK_H1FeKUZ7PglCsRIblXVtpKRMDQvI-nMwWOs_NE22yrQ==','gAAAAABp2ATGkmR85NXTdAgNrnGaWnVKwsRU9X2g-uXuMtPRF0C6f29ndLPO_di-cjIqBwNy4E5wnYmUknqgxP6pfRpojVVSMA=='),(6,9,'https://toddenergy.fldata.com/qazwsx1945.aspx','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp2AUoXf8uxcTwxUwXOCt5LzrHEpx-W-c7nstgKB-yESWdmUob186stFB4i2PsnH6L7GDevE37yCgAfzH0Sj6Elbrn_g==','gAAAAABp2AUoSnHFtXe-Q_kXbSyyqIfePAE8YoYnrJ4GGTnMC_xT1_CJ2qo743JojJ4WkIOi2BBAgonguhzpcEgKJGdcksO--Q=='),(7,10,'https://cvr.fldata.com','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp2AV6Hrtn5t64CNdvor1-TUlz6zogBBQxKNXI6h7MYmKyBxmgG7v8w1mftUHzua_JSeHqHi74nA4LYjoVXna9uGTd1w==','gAAAAABp2AV79Q9HCDTL1HK-o3cFTKPsSyIZW7JI857yyR4zpFvEZehVrhqEtCQhf5Z-MLW-SSIWRnTA1sJEQKWnSM5VQd4zIg=='),(8,11,'https://hsa.fldata.com','#USERID','#PASSWORD','#btnLogon','','mainpage.aspx','gAAAAABp2AYKgk3uhJcpsZzmOETM-IuVCq0iLOumTdSe_1bkm6hTlFqU7Q8neUkEputPkYK-VnmqwWtlqI8Y_dwmCNbySdcm1Q==','gAAAAABp2AYKKFOW7ogjl-3Eb5MK3yG4AYw3cIMu9nxQmiFw8czPpi32FsCo1_9Z9AVeNWO_fHA2vksEbHU97dJT3MkfVHpoiQ==');
/*!40000 ALTER TABLE `site_credentials` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `site_pages`
--

DROP TABLE IF EXISTS `site_pages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `site_pages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `site_id` int DEFAULT NULL,
  `page_url` varchar(500) NOT NULL,
  `page_name` varchar(255) DEFAULT NULL,
  `expected_element` varchar(255) DEFAULT NULL,
  `expected_text` varchar(500) DEFAULT NULL,
  `sort_order` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `site_id` (`site_id`),
  CONSTRAINT `site_pages_ibfk_1` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `site_pages`
--

LOCK TABLES `site_pages` WRITE;
/*!40000 ALTER TABLE `site_pages` DISABLE KEYS */;
INSERT INTO `site_pages` VALUES (2,NULL,'https://ehsqa3.fldata.com/app/dashboard','App Dashboard','','',0);
/*!40000 ALTER TABLE `site_pages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sites`
--

DROP TABLE IF EXISTS `sites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sites` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `url` varchar(500) NOT NULL,
  `check_type` enum('UPTIME','LOGIN','MULTI_PAGE') DEFAULT NULL,
  `check_interval_minutes` int DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `notification_channel` enum('EMAIL','TEAMS','BOTH') DEFAULT NULL,
  `notification_emails` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sites`
--

LOCK TABLES `sites` WRITE;
/*!40000 ALTER TABLE `sites` DISABLE KEYS */;
INSERT INTO `sites` VALUES (1,'ehsqa4.fldata.com','https://ehsqa4.fldata.com','LOGIN',10,1,'EMAIL','isingh@fldata.com','2026-04-09 12:37:05','2026-04-09 20:12:00'),(7,'OXY','https://oxy.fldata.com','LOGIN',3,1,'BOTH','isingh@fldata.com','2026-04-09 19:56:20','2026-04-09 19:56:20'),(8,'Total','https://totalenergies.fldata.com','LOGIN',3,1,'BOTH','isingh@fldata.com','2026-04-09 19:57:58','2026-04-09 19:57:58'),(9,'TODD','https://toddenergy.fldata.com','LOGIN',3,1,'BOTH','isingh@fldata.com','2026-04-09 19:59:36','2026-04-09 19:59:36'),(10,'CVR','https://cvr.fldata.com','LOGIN',3,1,'BOTH','isingh@fldata.com','2026-04-09 20:00:58','2026-04-09 20:00:58'),(11,'HSA','https://hsa.fldata.com','LOGIN',3,1,'BOTH','isingh@fldata.com','2026-04-09 20:02:14','2026-04-09 20:02:14');
/*!40000 ALTER TABLE `sites` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `key` varchar(255) NOT NULL,
  `value` text NOT NULL,
  `is_encrypted` tinyint(1) DEFAULT NULL,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_system_settings_key` (`key`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_settings`
--

LOCK TABLES `system_settings` WRITE;
/*!40000 ALTER TABLE `system_settings` DISABLE KEYS */;
INSERT INTO `system_settings` VALUES (1,'smtp_host','smtp.sendgrid.net',0,'2026-04-09 20:09:31'),(2,'smtp_port','587',0,'2026-04-09 15:56:12'),(3,'smtp_user','apikey',0,'2026-04-09 20:09:31'),(4,'smtp_password','gAAAAABp2Ad7CraxGt_YtH2mZvlB9XjK_ULl90FsI2mQK4bRJuaY1pathfMWGFLvwqUi7kdXX72wZtOh2DwDdAC2Fm-x59lpqm2D7zOdn9t1YKWTR49PBMYuoWCs4F4vX65cUtqAspT1zRLaAgNmkvtNl_aE1H1IUJRWJG5S_LFNoVvZOpz9C8Y=',1,'2026-04-09 20:09:31'),(5,'smtp_from_email','noreply@fldata.com',0,'2026-04-09 20:09:31'),(6,'smtp_use_tls','true',0,'2026-04-09 15:56:12'),(7,'teams_webhook_url','gAAAAABp1-BpsMV2hb_Too555Ii_1QBQqHYyD7NoDh_XKrWVtw2SFZJYEBizmjf9XrxknNO5YFrYWVtrw4brODZ0_A6WSzSpLTqRGi3etU8VpKRnMiDWrYfl_tOPnmxAJLGe3dPRyZZqQJ2BwCCzof3NvjexcgZzDcbNe5SeKKzwEuH-6vJE7f6FSTCE7bfTLI6UiE3cW0wlBQoFrjlmgnpObZD9e_0wVdY_Wxh7oASDPwKROjtsXJ2GBvFhdHB97uTKNxr-JAMihVzr7ok0P3sXShoTEQzsQjrueD1Qx445wabF1ie0kREqU-tMIr4PX4qWj9VAHggpq6GrUTWRvUCp2usegTDuVRPHW9mct2JV2DJ7rClYG6k6VZWTNWPaTFR_Q0lkd8XZZ48AQ28F7SE30a4ls7_sujh0bfPzGYgoQM-JQggKS_M=',1,'2026-04-09 17:22:49');
/*!40000 ALTER TABLE `system_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `hashed_password` varchar(255) NOT NULL,
  `full_name` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `is_admin` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (3,'isingh@fldata.com','$2b$12$/QS2P4rZX7xMnTB.gnDX5OfAveFPm99s6CfwWCu9nmxnM6ar0Xsvy','FL Admin',1,1,'2026-04-09 19:32:14');
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

-- Dump completed on 2026-04-09 20:21:52
