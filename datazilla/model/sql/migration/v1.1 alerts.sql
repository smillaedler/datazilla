
DELIMITER ;;

DROP PROCEDURE IF EXISTS exec;;
CREATE PROCEDURE exec(
	sqltext		VARCHAR(8000),
	ignore_error 	TINYINT
)
BEGIN
	IF ignore_error=1 THEN BEGIN
		DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END;
		SET @temp=sqltext;
		PREPARE stmt FROM @temp;
		EXECUTE stmt;
		DEALLOCATE PREPARE stmt;
	END; ELSE BEGIN
		SET @temp=sqltext;
		PREPARE stmt FROM @temp;
		EXECUTE stmt;
		DEALLOCATE PREPARE stmt;
	END; END IF;
END;;



DROP PROCEDURE IF EXISTS get_version;;
CREATE PROCEDURE get_version(
	OUT version VARCHAR(10)
) BEGIN
	DECLARE is_version_1 INTEGER;
	DECLARE schema_name VARCHAR(80);
	
	SELECT DATABASE() INTO schema_name FROM DUAL;
	
	SELECT count(1) INTO is_version_1 FROM information_schema.tables WHERE table_schema=schema_name AND table_name='version';
	IF (is_version_1=0) THEN 
		CALL exec(concat('CREATE TABLE ', schema_name, '.version (id	VARCHAR(10))'), false);
		CALL exec(concat('INSERT INTO ', schema_name, '.version VALUES (''1.0'')'), false);
		SET version='1.0';
	ELSE 
		SET @version='1.0';
		CALL exec(concat('SELECT max(id) INTO @version FROM ', schema_name, '.version'), false);
		SET version=@version;
	END IF;	
END;;


DROP FUNCTION IF EXISTS bayesian_add;;
CREATE FUNCTION bayesian_add (
	a	DOUBLE,
	b	DOUBLE
) 
	RETURNS DOUBLE
 	DETERMINISTIC
	NO SQL
BEGIN
	RETURN a*b/(a*b+(1-a)*(1-b));
END;;



DROP PROCEDURE IF EXISTS `migrate v1.1`;;
CREATE PROCEDURE `migrate v1.1` ()
m11: BEGIN
	DECLARE version VARCHAR(10);
	
	CALL get_version(version);
	IF (version<>'1.0') THEN
		LEAVE m11;
	END IF;
	
	
	DROP TABLE IF EXISTS alert_mail;
	DROP TABLE IF EXISTS alert_mail_reasons;
	DROP TABLE IF EXISTS alert_mail_states;
	DROP TABLE IF EXISTS alert_mail_listeners;
	DROP TABLE IF EXISTS alter_mail_thresholds;
	
	CREATE TABLE alert_mail_states(
		code			VARCHAR(10) NOT NULL PRIMARY KEY
	);
	INSERT INTO alert_mail_states VALUES ('new');		
	INSERT INTO alert_mail_states VALUES ('sent');
	INSERT INTO alert_mail_states VALUES ('obsolete');	##MAYBE THIS IS USEFUL


	CREATE TABLE alert_mail_reasons (
		code			VARCHAR(80) NOT NULL PRIMARY KEY,
		description		VARCHAR(2000), ##MORE DETAILS ABOUT WHAT THIS IS
		last_run		DATETIMe NOT NULL,
		config			VARCHAR(8000)
	);
	INSERT INTO alert_mail_reasons VALUES (
		'page_threshold_limit', 
		'The page has performed badly (${expected}), ${actual} or less was expected'
		date_add(UTC_TIMESTAMP(), INTERVAL -30 DAY),
		null
	);		
	INSERT INTO alert_mail_reasons VALUES (
		'exception_point', 
		'The test has performed worse then usual by ${amount} standard deviations (${confidence})'
		date_add(UTC_TIMESTAMP(), INTERVAL -30 DAY),
		'{"minOffset":0.999}'
	);		


	CREATE TABLE alert_mail_page_thresholds (
		page_id			INTEGER NOT NULL PRIMARY KEY,
		threshhold		DECIMAL(20, 10) NOT NULL,
		severity		DOUBLE NOT NULL, 
		reason			VARCHAR(2000) NOT NULL,
		time_added		DATETIME NOT NULL,
		contact			VARCHAR(200) NOT NULL,
		FOREIGN KEY (test_id) REFERENCES pages(id) 
	);
	
	INSERT INTO alert_mail_page_thresholds
	SELECT
		p.id
		200,
		0.5,
		"(amazon.com) because I like to complain",
		UTC_TIMESTAMP(),
		"klahnakoski@mozilla.com"
	FROM
		pages p 
	WHERE
		p.url='amazon.com'
	;
	

	CREATE TABLE alert_mail_listeners (
		email			VARCHAR(200) NOT NULL PRIMARY KEY
	);
	INSERT INTO alert_mail_listeners VALUES ('klahnakoski@mozilla.com');

	
	CREATE TABLE alert_mail (
		id 				INTEGER NOT NULL PRIMARY KEY,
		mail_state 		VARCHAR(10) NOT NULL,  ##WHAT THE MAILER HAS DONE WITH THIS ALERT 
		create_time		DATETIME NOT NULL,		##WHEN THIS ISSUE WAS FIRST IDENTIFIED
		last_updated	DATETIME NOT NULL, 	##WHEN THIS ISSUE WAS LAST UPDATED WITH NEW INFO
		last_sent		DATETIME,			##WHEN THIS ISSUE WAS LAST SENT TO EMAIL
		test_run		INTEGER NOT NULL, 	##REFERENCE THE TEST 
		reason			VARCHAR(20) NOT NULL,  ##REFERNCE TO STANDARD SET OF REASONS
		details			VARCHAR(2000) NOT NULL, ##JSON OF SPECIFIC DETAILS
		severity		DOUBLE NOT NULL,		##ABSTRACT SEVERITY 1.0==HIGH, 0.0==LOW
		confidence		DOUBLE NOT NULL,		##CONFIDENCE INTERVAL 1.0==100% CONFIDENCE
		solution		VARCHAR(40), ##INTENT FOR HUMANS TO MARKUP THIS ALERT SO MACHINE KNOWS IF REAL, OR START ESCALATING
		INDEX alert_lookup (test_run),
		FOREIGN KEY alert_mail_test_run (test_run) REFERENCES test_run(id),
		FOREIGN KEY alert_mail_mail_state (mail_state) REFERENCES alert_mail_states(code),
		FOREIGN KEY alert_mail_reason (reason) REFERENCES alert_mail_reasons(code)
	);
	
	UPDATE `version` SET id='1.1';
	
END;;


CALL `migrate v1.1`();;
COMMIT;;








