-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2026-05-07 15:25:51
-- 服务器版本： 5.7.44-log
-- PHP 版本： 8.0.26

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 数据库： `funds`
--

-- --------------------------------------------------------

--
-- 表的结构 `admins`
--

CREATE TABLE `admins` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `salt` varchar(32) NOT NULL,
  `real_name` varchar(50) DEFAULT '',
  `email` varchar(100) DEFAULT '',
  `status` tinyint(4) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_login` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `admins`
--

INSERT INTO `admins` (`id`, `username`, `password`, `salt`, `real_name`, `email`, `status`, `created_at`, `updated_at`, `last_login`) VALUES
(2, 'admin', 'f868f45e03360ef5fca7b7a9144f45651b3f0920e8db44372f506fbc21bc2b5f', 'fundquant_salt_2026', '系统管理员', '', 1, '2026-04-13 17:15:16', '2026-05-07 15:18:52', '2026-05-07 15:18:53');

-- --------------------------------------------------------

--
-- 表的结构 `ai_models`
--

CREATE TABLE `ai_models` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `type` varchar(50) NOT NULL,
  `api_url` varchar(500) NOT NULL,
  `api_key` varchar(255) DEFAULT '',
  `model_id` varchar(100) NOT NULL,
  `timeout` int(11) DEFAULT '30',
  `temperature` decimal(4,2) DEFAULT '0.50',
  `max_tokens` int(11) DEFAULT '300',
  `is_default` tinyint(4) DEFAULT '0',
  `status` tinyint(4) DEFAULT '1',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `ai_models`
--

INSERT INTO `ai_models` (`id`, `name`, `type`, `api_url`, `api_key`, `model_id`, `timeout`, `temperature`, `max_tokens`, `is_default`, `status`, `remark`, `created_at`, `updated_at`) VALUES
(1, 'MiniMax v2 (环境变量初始化)', 'chat', 'https://api.minimaxi.com/anthropic/v1/messages', 'gAAAAABp3LmMd5c6GkKoFWb2y8es1T0mXJoLiWpJuQyhmQVMFsI2TiE-Ks2mrJoLciiWv-uxWxuv8M_FBnyaUJcFhOff2bBP22ykc7Nn8ua8ydFgc85d8rVJdKgD87JfQw8XVmf2XWrbR-kEKmOTeq8qT653qtgzLGIAo3FOyyJs731odzISyvifoLp9N3GAPlHMY08tbv71VgTLWu2WPOXWl4f1PB57WHCStn4pqRwBMWrcZ_HfxMQ=', 'MiniMax-M2.7-highspeed', 30, 0.50, 300, 1, 1, NULL, '2026-04-13 17:38:20', '2026-04-13 17:38:20'),
(2, 'dp', 'chat', 'https://api.deepseek.com/anthropic', 'gAAAAABp_D1cLlxz1wB6Dt63QWBhuKjd-RAZHOo3PVOG2qRCXDa8K68Ykl4iO2H0rMXqpCkjZVo7gA8Vl_e_SeBiRdKBbPBgmaqujtk3tnYhP17qZFT9kF8_4qihAEDQA_2oFxwZwIgB', 'deepseek-v4-flash', 30, 0.50, 300, 0, 1, '', '2026-05-07 15:21:01', '2026-05-07 15:21:01');

-- --------------------------------------------------------

--
-- 表的结构 `api_configs`
--

CREATE TABLE `api_configs` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `provider` varchar(50) NOT NULL,
  `api_url` varchar(500) NOT NULL,
  `api_key` varchar(255) DEFAULT '',
  `rate_limit` int(11) DEFAULT '100',
  `status` tinyint(4) DEFAULT '1',
  `last_check` datetime DEFAULT NULL,
  `last_response` int(11) DEFAULT '0',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `feishu_settings`
--

CREATE TABLE `feishu_settings` (
  `id` int(11) NOT NULL,
  `webhook_url` varchar(500) DEFAULT '' COMMENT '飞书Webhook地址',
  `enabled` int(11) DEFAULT '0' COMMENT '是否启用 0-关闭 1-开启',
  `push_condition` varchar(50) DEFAULT 'all' COMMENT '推送条件: all-全部 profit-仅盈利 loss-仅亏损',
  `secret_key` varchar(200) DEFAULT '' COMMENT '签名密钥(可选)',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `feishu_settings`
--

INSERT INTO `feishu_settings` (`id`, `webhook_url`, `enabled`, `push_condition`, `secret_key`, `created_at`, `updated_at`) VALUES
(1, 'https://open.feishu.cn/open-apis/bot/v2/hook/5c72e166-134c-46ec-b4f1-7d1182a9b35c', 1, 'all', '', '2026-04-15 16:33:20', '2026-04-15 17:02:12');

-- --------------------------------------------------------

--
-- 表的结构 `holdings`
--

CREATE TABLE `holdings` (
  `id` int(11) NOT NULL,
  `code` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `shares` decimal(12,4) DEFAULT '0.0000',
  `cost` decimal(10,4) DEFAULT '0.0000',
  `nav` decimal(10,4) DEFAULT '0.0000',
  `amount` decimal(12,2) DEFAULT '0.00',
  `profit` decimal(12,2) DEFAULT '0.00',
  `profit_pct` decimal(8,2) DEFAULT '0.00',
  `note` text,
  `status` tinyint(4) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `holdings`
--

INSERT INTO `holdings` (`id`, `code`, `name`, `shares`, `cost`, `nav`, `amount`, `profit`, `profit_pct`, `note`, `status`, `created_at`, `updated_at`) VALUES
(2, '021363', '易方达中证沪深港黄金产业股票指数C', 3305.5600, 2.1328, 1.8880, 6549.84, -786.93, -12.01, '', 1, '2026-04-13 17:36:04', '2026-05-06 07:47:26'),
(3, '011452', '华泰柏瑞质量成长混合C', 1143.6400, 1.8885, 2.5416, 4319.63, 1482.29, 34.32, '', 1, '2026-04-13 17:36:04', '2026-04-16 22:09:17'),
(4, '002611', '博时黄金ETF联接C', 937.3600, 3.3582, 3.2780, 3074.26, -56.76, -1.85, '', 1, '2026-04-13 17:36:04', '2026-04-23 09:02:18'),
(5, '014855', '嘉实中证半导体产业指数增强C', 4018.9300, 2.1623, 2.1471, 10419.00, -4.82, -0.05, '', 1, '2026-04-13 17:36:04', '2026-04-23 08:57:38'),
(6, '020065', '西部利得科技创新混合C', 887.3500, 1.8928, 1.7621, 6718.18, -538.34, -8.01, '', 1, '2026-04-13 17:36:04', '2026-04-23 09:01:13'),
(7, '017470', '嘉实上证科创板芯片ETF联接C', 0.0000, 2.0337, 2.1199, 2300.01, 80.30, 3.49, '', 1, '2026-04-13 17:36:04', '2026-04-23 08:57:50'),
(8, '013403', '华夏恒生科技ETF联接(QDII)C', 5155.5800, 0.9431, 0.7972, 4862.49, -719.47, -14.80, '', 1, '2026-04-13 17:36:04', '2026-04-16 22:07:29'),
(10, '015790', '永赢高端装备智选混合C', 4608.4200, 1.5000, 1.3847, 7160.10, 0.00, 0.00, '测试', 0, '2026-04-14 07:56:44', '2026-04-15 08:04:30'),
(18, 'TEST01', '测试', 1.0000, 1.0000, 0.0000, 1.00, 0.00, 0.00, '', 0, '2026-04-15 00:44:35', '2026-04-15 00:44:35'),
(19, '510300', '沪深300ETF', 2000.0000, 4.5000, 0.0000, 4500.00, 0.00, 0.00, '', 0, '2026-04-15 00:45:53', '2026-04-15 00:45:53'),
(20, '015790', '永赢高端装备智选混合C', 1423.8000, 1.5406, 0.0000, 6912.63, 0.00, 0.00, '', 1, '2026-04-15 08:04:44', '2026-05-06 07:46:08'),
(21, '510300', '沪深300ETF华泰柏瑞', 1.0000, 1.0000, 0.0000, 1.00, 0.00, 0.00, '', 0, '2026-04-15 09:10:54', '2026-04-15 09:11:12'),
(22, '510300', '沪深300ETF华泰柏瑞', 0.0000, 1000.0000, 0.0000, 0.00, 0.00, 0.00, '', 0, '2026-04-15 09:21:24', '2026-04-15 09:29:19'),
(23, '000171', '易方达高等级信用债A', 0.0000, 0.0000, 0.0000, 0.00, 0.00, 0.00, '', 0, '2026-04-15 15:11:51', '2026-04-15 15:12:07'),
(24, '000171', '易方达高等级信用债A', 1.0000, 0.0000, 0.0000, 0.00, 0.00, 0.00, '', 0, '2026-04-15 16:05:27', '2026-04-15 16:05:44'),
(25, '161226', '', 534.0000, 2.5200, 0.0000, 1345.68, 0.00, 0.00, '', 1, '2026-04-23 08:59:38', '2026-04-23 08:59:38'),
(26, '018957', '中航机遇领航混合发起C', 250.0000, 4.6480, 0.0000, 1162.00, 0.00, 0.00, '', 1, '2026-05-06 07:50:36', '2026-05-06 07:50:36'),
(27, '159967', '创业板成长ETF华夏', 0.0000, 0.0000, 0.0000, 0.00, 0.00, 0.00, '', 0, '2026-05-07 15:03:16', '2026-05-07 15:21:51'),
(28, '159381', '创业板人工智能ETF华夏', 0.0000, 0.0000, 0.0000, 0.00, 0.00, 0.00, '', 0, '2026-05-07 15:03:24', '2026-05-07 15:21:48'),
(29, '512400', '有色金属ETF南方', 0.0000, 0.0000, 0.0000, 0.00, 0.00, 0.00, '', 0, '2026-05-07 15:03:53', '2026-05-07 15:21:44');

-- --------------------------------------------------------

--
-- 表的结构 `login_logs`
--

CREATE TABLE `login_logs` (
  `id` int(11) NOT NULL,
  `admin_id` int(11) DEFAULT NULL,
  `username` varchar(50) NOT NULL,
  `ip` varchar(50) DEFAULT '',
  `user_agent` text,
  `login_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `status` varchar(20) DEFAULT 'success',
  `fail_reason` varchar(100) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `login_logs`
--

INSERT INTO `login_logs` (`id`, `admin_id`, `username`, `ip`, `user_agent`, `login_time`, `status`, `fail_reason`) VALUES
(1, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-13 17:16:23', 'success', ''),
(2, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-13 17:17:47', 'success', ''),
(3, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1 Lark/7.65.10 LarkLocale/zh_CN ChannelName/Feishu appid/1378; appname/Feishu; LKBrowserIdentifier/582518EC-0BC7-43D6-8C9D-7829311670D7', '2026-04-13 17:18:54', 'success', ''),
(4, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.251 Safari/537.36', '2026-04-13 17:22:20', 'success', ''),
(5, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-13 17:42:04', 'success', ''),
(6, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-13 17:42:15', 'success', ''),
(7, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.200 Safari/537.36 Qaxbrowser', '2026-04-13 17:43:57', 'success', ''),
(8, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-13 21:19:01', 'success', ''),
(9, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-14 20:13:36', 'failed', '密码错误'),
(10, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-14 20:13:51', 'failed', '密码错误'),
(11, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-14 20:13:53', 'failed', '密码错误'),
(12, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-14 20:14:57', 'success', ''),
(13, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-14 20:15:06', 'success', ''),
(14, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-14 20:42:22', 'failed', '密码错误'),
(15, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-14 21:36:46', 'success', ''),
(16, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:18', 'failed', '密码错误'),
(17, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:18', 'failed', '密码错误'),
(18, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:35', 'failed', '密码错误'),
(19, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:36', 'failed', '密码错误'),
(20, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:36', 'failed', '密码错误'),
(21, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:36', 'failed', '密码错误'),
(22, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:36', 'failed', '密码错误'),
(23, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:36', 'failed', '密码错误'),
(24, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:45', 'success', ''),
(25, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:53', 'success', ''),
(26, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:41:57', 'success', ''),
(27, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:42:03', 'success', ''),
(28, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-15 00:44:37', 'success', ''),
(29, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:37:42', 'failed', '密码错误'),
(30, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:37:58', 'failed', '密码错误'),
(31, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:38:00', 'failed', '密码错误'),
(32, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:47:59', 'failed', '密码错误'),
(33, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:48:00', 'failed', '密码错误'),
(34, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:54:38', 'success', ''),
(35, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 16:58:00', 'success', ''),
(36, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 17:00:16', 'success', ''),
(37, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.0.0 Safari/537.36', '2026-04-15 17:08:57', 'success', ''),
(38, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1 Lark/7.65.10 LarkLocale/zh_CN ChannelName/Feishu appid/1378; appname/Feishu; LKBrowserIdentifier/38DB11D6-E897-4189-AC3A-1F0CF97AFEFA', '2026-04-15 17:13:15', 'success', ''),
(39, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-15 17:19:07', 'success', ''),
(40, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.0.0 Safari/537.36', '2026-04-15 17:21:48', 'success', ''),
(41, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1 Lark/7.65.10 LarkLocale/zh_CN ChannelName/Feishu appid/1378; appname/Feishu; LKBrowserIdentifier/1F9A6F6A-0677-4089-8670-E219ABBC09EC', '2026-04-15 17:30:26', 'success', ''),
(42, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1 Lark/7.65.10 LarkLocale/zh_CN ChannelName/Feishu appid/1378; appname/Feishu; LKBrowserIdentifier/FC48C827-698E-44FE-AD2C-25B8FD69E18D', '2026-04-15 19:40:23', 'success', ''),
(43, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.0.0 Safari/537.36', '2026-04-16 09:00:40', 'failed', '密码错误'),
(44, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-16 09:00:49', 'failed', '密码错误'),
(45, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-16 09:01:57', 'success', ''),
(46, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-16 09:37:14', 'success', ''),
(47, 2, 'admin', '127.0.0.1', 'curl/7.88.1', '2026-04-16 09:40:40', 'success', ''),
(48, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.0.0 Safari/537.36', '2026-04-16 09:41:28', 'success', ''),
(49, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-16 09:46:21', 'success', ''),
(50, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.0.0 Safari/537.36', '2026-04-16 09:54:03', 'success', ''),
(51, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-16 10:00:06', 'success', ''),
(52, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/145.0.0.0 Safari/537.36', '2026-04-16 10:00:34', 'success', ''),
(53, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-16 10:01:14', 'success', ''),
(54, 2, 'admin', '127.0.0.1', 'curl/8.5.0', '2026-04-16 10:01:44', 'success', ''),
(55, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-16 10:50:31', 'success', ''),
(56, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36', '2026-04-16 22:06:17', 'success', ''),
(57, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0', '2026-04-18 14:46:24', 'success', ''),
(58, 2, 'admin', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:150.0) Gecko/20100101 Firefox/150.0', '2026-05-07 15:18:52', 'success', '');

-- --------------------------------------------------------

--
-- 表的结构 `operation_logs`
--

CREATE TABLE `operation_logs` (
  `id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `module` varchar(50) NOT NULL,
  `action` varchar(50) NOT NULL,
  `target_type` varchar(50) DEFAULT '',
  `target_id` int(11) DEFAULT NULL,
  `detail` text,
  `ip` varchar(50) DEFAULT '',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `operation_logs`
--

INSERT INTO `operation_logs` (`id`, `admin_id`, `module`, `action`, `target_type`, `target_id`, `detail`, `ip`, `created_at`) VALUES
(1, 2, 'settings', 'config', 'system_setting', NULL, '设置 site_title = FundQuant 管理后台', '127.0.0.1', '2026-04-16 09:40:52'),
(2, 2, 'settings', 'config', 'system_setting', NULL, '设置 page_size = 20', '127.0.0.1', '2026-04-16 09:41:00'),
(3, 2, 'settings', 'config', 'system_setting', NULL, '设置 cache_enabled = true', '127.0.0.1', '2026-04-16 09:41:00'),
(4, 2, 'settings', 'config', 'system_setting', NULL, '设置 auto_refresh = false', '127.0.0.1', '2026-04-16 09:41:00'),
(5, 2, 'settings', 'config', 'system_setting', NULL, '设置 max_holdings = 50', '127.0.0.1', '2026-04-16 09:41:00');

-- --------------------------------------------------------

--
-- 表的结构 `system_settings`
--

CREATE TABLE `system_settings` (
  `id` int(11) NOT NULL,
  `setting_key` varchar(100) NOT NULL,
  `setting_value` text,
  `setting_type` varchar(20) DEFAULT 'string',
  `remark` varchar(255) DEFAULT '',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转存表中的数据 `system_settings`
--

INSERT INTO `system_settings` (`id`, `setting_key`, `setting_value`, `setting_type`, `remark`, `updated_at`) VALUES
(1, 'site_title', 'FundQuant 管理后台', 'string', '网站标题', '2026-04-16 09:40:52'),
(2, 'page_size', '20', 'int', '默认分页数', '2026-04-16 09:40:59'),
(3, 'cache_enabled', 'true', 'string', '缓存开关', '2026-04-16 09:40:59'),
(4, 'auto_refresh', 'false', 'string', '自动刷新', '2026-04-16 09:41:00'),
(5, 'max_holdings', '50', 'int', '最大持仓数', '2026-04-16 09:41:00');

--
-- 转储表的索引
--

--
-- 表的索引 `admins`
--
ALTER TABLE `admins`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD KEY `idx_username` (`username`);

--
-- 表的索引 `ai_models`
--
ALTER TABLE `ai_models`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_type` (`type`);

--
-- 表的索引 `api_configs`
--
ALTER TABLE `api_configs`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `feishu_settings`
--
ALTER TABLE `feishu_settings`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `holdings`
--
ALTER TABLE `holdings`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_code` (`code`);

--
-- 表的索引 `login_logs`
--
ALTER TABLE `login_logs`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `operation_logs`
--
ALTER TABLE `operation_logs`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `system_settings`
--
ALTER TABLE `system_settings`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `setting_key` (`setting_key`);

--
-- 在导出的表使用AUTO_INCREMENT
--

--
-- 使用表AUTO_INCREMENT `admins`
--
ALTER TABLE `admins`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- 使用表AUTO_INCREMENT `ai_models`
--
ALTER TABLE `ai_models`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- 使用表AUTO_INCREMENT `api_configs`
--
ALTER TABLE `api_configs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `feishu_settings`
--
ALTER TABLE `feishu_settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- 使用表AUTO_INCREMENT `holdings`
--
ALTER TABLE `holdings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=30;

--
-- 使用表AUTO_INCREMENT `login_logs`
--
ALTER TABLE `login_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=59;

--
-- 使用表AUTO_INCREMENT `operation_logs`
--
ALTER TABLE `operation_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- 使用表AUTO_INCREMENT `system_settings`
--
ALTER TABLE `system_settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
