-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Erstellungszeit: 25. Jun 2024 um 08:10
-- Server-Version: 10.5.23-MariaDB-0+deb11u1
-- PHP-Version: 8.3.6

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

--
-- Datenbank: `redditanalyzer`
--

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `analysis_results`
--

CREATE TABLE `analysis_results` (
  `id` int(11) NOT NULL,
  `user_id` varchar(255) DEFAULT NULL,
  `topic` varchar(255) DEFAULT NULL,
  `subreddit` varchar(255) DEFAULT NULL,
  `post_id` varchar(255) DEFAULT NULL,
  `post_title` text DEFAULT NULL,
  `analysis` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `business_model_title` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `user_profiles`
--

CREATE TABLE `user_profiles` (
  `user_id` varchar(255) NOT NULL,
  `educational_background` text DEFAULT NULL,
  `professional_experience` text DEFAULT NULL,
  `skills` text DEFAULT NULL,
  `availability` enum('Full time','Side hustle','Both possible') DEFAULT NULL,
  `other_criteria` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

--
-- Indizes der exportierten Tabellen
--

--
-- Indizes für die Tabelle `analysis_results`
--
ALTER TABLE `analysis_results`
  ADD PRIMARY KEY (`id`);

--
-- Indizes für die Tabelle `user_profiles`
--
ALTER TABLE `user_profiles`
  ADD PRIMARY KEY (`user_id`);

--
-- AUTO_INCREMENT für exportierte Tabellen
--

--
-- AUTO_INCREMENT für Tabelle `analysis_results`
--
ALTER TABLE `analysis_results`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;
