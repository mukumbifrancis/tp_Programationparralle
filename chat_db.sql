-- MySQL dump 10.13  Distrib 8.0.45, for Linux (x86_64)
--
-- Host: localhost    Database: chat_db
-- ------------------------------------------------------
-- Server version	8.0.45-0ubuntu0.24.04.1

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
-- Table structure for table `chat_messages`
--

DROP TABLE IF EXISTS `chat_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `sent_at` datetime NOT NULL,
  `sender` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mode` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recipients` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `ciphertext` text COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `chat_messages`
--

LOCK TABLES `chat_messages` WRITE;
/*!40000 ALTER TABLE `chat_messages` DISABLE KEYS */;
INSERT INTO `chat_messages` VALUES (1,'2026-02-13 10:34:44','h','private','bb','gAAAAABpjuIj5Bq9Emh9wacIkrMSUQr7wL1UYFexspGKuuoV3yE-COkbDA1yHbAq-s5QBIYkNlqVFc12wD-cpjcnz4lgSPhaQA=='),(2,'2026-02-13 10:35:24','hh','broadcast','h','gAAAAABpjuJLwHV_-pkfxmsXaCFnUpVGdiHPNDHsgQllXmPqCaeiK0hpM0tA-pFO52bf93kP0Zpva5-88LqbGD7dZ4urFOOgFw=='),(3,'2026-02-13 15:12:37','aaaa','private','nembo','gAAAAABpjyNFzQvMgfBeSQeJEiWWaZg3xccmLXQQVTDUD4N23nmgua7-2DnDkh3M2S79Dtpz6j3Ze3fyAfouVNvdIe21gzWIEw=='),(4,'2026-02-13 15:13:17','nembo','private','aaaa','gAAAAABpjyNsex3lyF5tM7vJnorZoa4ZRe0xOEE82nsqyWmBiiRZgk4shzFGDwfzIv25exz6a_LBCcokxMt17cTs2w3glijmig=='),(5,'2026-02-13 15:21:50','h','private','ggg','gAAAAABpjyVufKSRQmXOZGc-vkGuwOHdBbfesmZLT3YUvOic_Ey07P44g-ePkLSWVqQpuz6ifkijY8oWtv0K11cglebRIYHsSg=='),(6,'2026-02-14 10:55:16','h','broadcast','','gAAAAABpkDhz3OSmkKGdgsmtkP5vVmEMVxTFJTD-1HaDiV9abRibMD5Mfaugtd4_VA71hEfUoKqm4epUgtZtitxp1IV3ctscSg=='),(7,'2026-02-14 10:58:07','h1','broadcast','','gAAAAABpkDkeJcaGajcOvg3Dsf8pvGJFDwFG2p-79vLNrq4QFQvJ-NOXe5P-XueYFbCzA0lKd5XCYs5gkDog3DMUF2uh6s0W0g=='),(8,'2026-02-14 10:58:40','h111','broadcast','','gAAAAABpkDlAHOg7Q30skAE_uAfqtB7vf4X9Nd7mNxe3JJYoCXNgMhIZ4729pglX1b67mv9b-suKjhjH5ur2ztd4cqqwv89zvQ=='),(9,'2026-02-14 11:01:04','z','private','a','gAAAAABpkDnPQR8OwGTCK1-zpjfxqlq6XLtCcq34GQFWqsMiUQMTOqmxQWXY1RqShr-1YIoKiUEHMNNGdJBeXD6DTcrO1_aUrQ=='),(10,'2026-02-14 11:02:43','a','broadcast','','gAAAAABpkDozZKrdPniRMjMy6PnYJ4P-hbSMjDSRb4efd9sm-AWR1MC8CR8ME64XdqcRbhUDqsed288JXoxgpONpgYEScTjj2A=='),(11,'2026-02-14 11:05:36','z','broadcast','a','gAAAAABpkDrf5ipOZbqQMSuFfEsJxyFkafZFS0KWYLFxN46dQrMXkkEf1x6n1L_8LFXjS4EGJcxpTpnk5Lsa5K0YTM5SXk_Yow=='),(12,'2026-02-14 11:13:43','h','group','a,z','gAAAAABpkDzH4UwwChQ2CNYxhUxgC6_tdEOWJVgGdBCe6jDwcvqvBzm9zBGrHsfuGZJYP7daZeOKXOYxTU_QDfbRyiLcOqdxRQ=='),(13,'2026-02-14 20:09:36','az','broadcast','','gAAAAABpkLpfBMhzweqZ0mZPBT_P7uW3PXnPH0XAFhWeZPftEkSnzRhOt3Z7hi0NoXswN0KcwZBjR62ADt5JOneuz2mfXka7rA=='),(14,'2026-02-14 20:18:17','az','broadcast','','gAAAAABpkLxpm3pZBFvotYzH_jk-8ZbKC9NxotUauZvkiE_yeU9b6uNUFABbVwhavK_Tnrlm59aHGb-wpYR4ZJCy9etgehq1VA==');
/*!40000 ALTER TABLE `chat_messages` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-04 14:47:12
