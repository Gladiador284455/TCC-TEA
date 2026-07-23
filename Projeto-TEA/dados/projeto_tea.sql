SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

-- --------------------------------------------------------
-- Tabela: responsaveis
CREATE TABLE IF NOT EXISTS `responsaveis` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `nome` VARCHAR(150) NOT NULL,
  `cpf` VARCHAR(14) UNIQUE,
  `telefone` VARCHAR(20),
  `email` VARCHAR(100),
  `data_cadastro` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- Tabela: criancas
CREATE TABLE IF NOT EXISTS `criancas` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `nome` VARCHAR(150) NOT NULL,
  `data_nascimento` DATE NOT NULL,
  `genero` VARCHAR(20),
  `observacoes` TEXT,
  `data_cadastro` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- Tabela Intermediária: crianca_responsavel
CREATE TABLE IF NOT EXISTS `crianca_responsavel` (
  `crianca_id` INT(11) NOT NULL,
  `responsavel_id` INT(11) NOT NULL,
  `parentesco` VARCHAR(50) COMMENT 'Ex: Mãe, Pai, Tutor, Terapeuta',
  PRIMARY KEY (`crianca_id`, `responsavel_id`),
  CONSTRAINT `fk_cr_crianca` FOREIGN KEY (`crianca_id`) REFERENCES `criancas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cr_responsavel` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------
-- Atualização da Tabela: tentativas
CREATE TABLE IF NOT EXISTS `tentativas` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `crianca_id` INT(11) NULL,
  `fase` VARCHAR(100) NOT NULL,
  `timestamp` DATETIME NOT NULL,
  `tempo_execucao` FLOAT NOT NULL,
  `precisao` FLOAT NOT NULL,
  `indice_hesitacao` FLOAT NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_tentativas_crianca` FOREIGN KEY (`crianca_id`) REFERENCES `criancas` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

COMMIT;