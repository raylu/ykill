DROP TABLE IF EXISTS `characters`;
DROP TABLE IF EXISTS `items`;
DROP TABLE IF EXISTS `item_costs`;
DROP TABLE IF EXISTS `kill_costs`;
DROP TABLE IF EXISTS `kills`;

CREATE TABLE `kills` (
	`kill_id` int unsigned NOT NULL,
	`solar_system_id` int NOT NULL,
	`kill_time` datetime NOT NULL,
	`moon_id` int unsigned NOT NULL,
	PRIMARY KEY (`kill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `characters` (
	`id` int unsigned NOT NULL AUTO_INCREMENT,
	`kill_id` int unsigned NOT NULL,
	`victim` tinyint(1) NOT NULL,
	`character_id` int unsigned NOT NULL,
	`character_name` varchar(64) NOT NULL,
	`ship_type_id` int NOT NULL,
	`alliance_id` int unsigned NOT NULL,
	`alliance_name` varchar(64) NOT NULL,
	`corporation_id` int unsigned NOT NULL,
	`corporation_name` varchar(64) NOT NULL,
	`faction_id` int NOT NULL,
	`faction_name` varchar(64) NOT NULL,
	`damage` int DEFAULT NULL,
	`final_blow` tinyint(1) DEFAULT NULL,
	`security_status` float DEFAULT NULL,
	`weapon_type_id` int DEFAULT NULL,
	PRIMARY KEY (`id`),
	CONSTRAINT `fk_char_km` FOREIGN KEY (`kill_id`) REFERENCES `kills` (`kill_id`),
	INDEX `character_id` (`character_id`),
	INDEX `character_name` (`character_name`),
	INDEX `alliance_id` (`alliance_id`),
	INDEX `alliance_name` (`alliance_name`),
	INDEX `corporation_id` (`corporation_id`),
	INDEX `corporation_name` (`corporation_name`),
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `items` (
	`id` int unsigned NOT NULL AUTO_INCREMENT,
	`kill_id` int unsigned NOT NULL,
	`type_id` int NOT NULL,
	`flag` tinyint(3) unsigned NOT NULL,
	`dropped` int unsigned NOT NULL,
	`destroyed` int unsigned NOT NULL,
	`singleton` tinyint(4) NOT NULL,
	PRIMARY KEY (`id`),
	CONSTRAINT `fk_item_km` FOREIGN KEY (`kill_id`) REFERENCES `kills` (`kill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `item_costs` (
	`type_id` int NOT NULL UNIQUE,
	`cost` bigint unsigned NOT NULL,
	PRIMARY KEY (`type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `kill_costs` (
	`kill_id` int unsigned NOT NULL UNIQUE,
	`cost` bigint unsigned NOT NULL,
	PRIMARY KEY (`kill_id`),
	CONSTRAINT `fk_kill_cost_km` FOREIGN KEY (`kill_id`) REFERENCES `kills` (`kill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;
