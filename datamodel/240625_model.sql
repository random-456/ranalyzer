-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: cranky-tu.87-106-159-152.plesk.page
-- Erstellungszeit: 25. Jun 2024 um 18:28
-- Server-Version: 10.5.23-MariaDB-0+deb11u1
-- PHP-Version: 8.2.8

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
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `topic` varchar(255) DEFAULT NULL,
  `subreddit` varchar(255) DEFAULT NULL,
  `post_id` varchar(255) DEFAULT NULL,
  `post_title` text DEFAULT NULL,
  `analysis` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `business_model_title` varchar(255) DEFAULT NULL,
  `job_id` varchar(36) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `api_request_logs`
--

CREATE TABLE `api_request_logs` (
  `id` int(11) NOT NULL,
  `api_type` enum('reddit','openai') NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `openai_model` varchar(50) DEFAULT NULL,
  `openai_tokens_used` int(11) DEFAULT NULL,
  `reddit_requests_count` int(11) DEFAULT NULL,
  `additional_info` text DEFAULT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `mass_analysis_jobs`
--

CREATE TABLE `mass_analysis_jobs` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `subreddit` varchar(255) NOT NULL,
  `total_posts` int(11) NOT NULL,
  `completed_posts` int(11) DEFAULT 0,
  `status` enum('pending','in_progress','completed','failed') DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `user_profiles`
--

CREATE TABLE `user_profiles` (
  `user_id` varchar(36) NOT NULL,
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
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_user_post` (`user_id`,`post_id`);

--
-- Indizes für die Tabelle `api_request_logs`
--
ALTER TABLE `api_request_logs`
  ADD PRIMARY KEY (`id`);

--
-- Indizes für die Tabelle `mass_analysis_jobs`
--
ALTER TABLE `mass_analysis_jobs`
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
-- AUTO_INCREMENT für Tabelle `api_request_logs`
--
ALTER TABLE `api_request_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;
