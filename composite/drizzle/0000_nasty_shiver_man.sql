CREATE TABLE `drawings` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`name` text NOT NULL,
	`sha256` text NOT NULL,
	`size` integer NOT NULL,
	`status` text NOT NULL,
	`metadata` text NOT NULL,
	`expected` integer NOT NULL,
	`revision` integer DEFAULT 1 NOT NULL,
	`reviewed_revision` integer,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_drawings_owner_updated` ON `drawings` (`owner`,`updated_at`);--> statement-breakpoint
CREATE TABLE `edits` (
	`id` text PRIMARY KEY NOT NULL,
	`drawing_id` text NOT NULL,
	`entity_id` text,
	`owner` text NOT NULL,
	`reason` text NOT NULL,
	`before_data` text NOT NULL,
	`after_data` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`drawing_id`) REFERENCES `drawings`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `idx_edits_drawing_time` ON `edits` (`drawing_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `entities` (
	`id` text PRIMARY KEY NOT NULL,
	`drawing_id` text NOT NULL,
	`ordinal` integer NOT NULL,
	`handle` text NOT NULL,
	`type` text NOT NULL,
	`space` text NOT NULL,
	`layer` text NOT NULL,
	`original` text NOT NULL,
	`data` text NOT NULL,
	`classification` text DEFAULT 'unclassified' NOT NULL,
	`notes` text DEFAULT '' NOT NULL,
	`version` integer DEFAULT 1 NOT NULL,
	FOREIGN KEY (`drawing_id`) REFERENCES `drawings`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_entities_drawing_ordinal` ON `entities` (`drawing_id`,`ordinal`);--> statement-breakpoint
CREATE INDEX `idx_entities_drawing_layer` ON `entities` (`drawing_id`,`layer`);