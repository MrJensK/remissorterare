#!/usr/bin/env python3
"""
Schemalagd körning av Remissorterare
Används för automatisk körning via cron eller Task Scheduler
"""

import os
import sys
import logging
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Lägg till projektmappen i Python-sökvägen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from remiss_sorterare import RemissSorterare
from config import *

# Konfigurera logging för schemalagd körning
log_file = f"scheduled_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=getattr(logging, LOG_NIVÅ),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScheduledRunner:
    """Hanterar schemalagd körning av remissorteraren"""
    
    def __init__(self, email_config=None):
        """
        Initierar schemalagd körning
        
        Args:
            email_config: Dictionary med e-postinställningar (valfritt)
        """
        self.email_config = email_config or {}
        self.start_time = datetime.now()
        self.success = False
        self.error_message = None
        
    def send_email_notification(self, subject, message):
        """Skickar e-postnotifiering"""
        if not self.email_config:
            logger.info("E-postnotifiering är inte konfigurerad")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config.get('from_email')
            msg['To'] = self.email_config.get('to_email')
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(
                self.email_config.get('smtp_server'),
                self.email_config.get('smtp_port', 587)
            )
            server.starttls()
            server.login(
                self.email_config.get('username'),
                self.email_config.get('password')
            )
            
            text = msg.as_string()
            server.sendmail(
                self.email_config.get('from_email'),
                self.email_config.get('to_email'),
                text
            )
            server.quit()
            
            logger.info("E-postnotifiering skickad")
        except Exception as e:
            logger.error(f"Fel vid skickande av e-post: {e}")
    
    def run(self):
        """Kör remissorteraren med felhantering"""
        logger.info("=" * 60)
        logger.info("STARTAR SCHEMALAGD KÖRNING AV REMISSORTERARE")
        logger.info(f"Tidpunkt: {self.start_time}")
        logger.info("=" * 60)
        
        try:
            # Skapa sorterare
            sorterare = RemissSorterare()
            
            # Kontrollera att input-mappen finns
            if not sorterare.input_mapp.exists():
                logger.warning(f"Input-mapp finns inte: {sorterare.input_mapp}")
                self.send_email_notification(
                    "Remissorterare - Varning",
                    f"Input-mappen {sorterare.input_mapp} finns inte. Kontrollera konfigurationen."
                )
                return
            
            # Räkna PDF-filer före bearbetning
            pdf_filer = list(sorterare.input_mapp.glob("*.pdf"))
            logger.info(f"Hittade {len(pdf_filer)} PDF-filer att bearbeta")
            
            if not pdf_filer:
                logger.info("Inga PDF-filer att bearbeta")
                self.send_email_notification(
                    "Remissorterare - Information",
                    "Inga nya PDF-filer att bearbeta."
                )
                return
            
            # Bearbeta alla PDF-filer
            sorterare.bearbeta_alla_pdf()
            
            # Kontrollera resultat
            self.success = True
            end_time = datetime.now()
            duration = end_time - self.start_time
            
            logger.info("=" * 60)
            logger.info("SCHEMALAGD KÖRNING SLUTFÖRD")
            logger.info(f"Tidpunkt: {end_time}")
            logger.info(f"Varaktighet: {duration}")
            logger.info("=" * 60)
            
            # Skicka framgångsnotifiering
            success_message = f"""
Remissorterare kördes framgångsrikt!

Tidpunkt: {self.start_time}
Varaktighet: {duration}
Antal PDF-filer: {len(pdf_filer)}

Loggfil: {log_file}
            """
            
            self.send_email_notification(
                "Remissorterare - Framgång",
                success_message
            )
            
        except Exception as e:
            self.success = False
            self.error_message = str(e)
            end_time = datetime.now()
            duration = end_time - self.start_time
            
            logger.error("=" * 60)
            logger.error("SCHEMALAGD KÖRNING MISSLYCKADES")
            logger.error(f"Fel: {e}")
            logger.error(f"Tidpunkt: {end_time}")
            logger.error(f"Varaktighet: {duration}")
            logger.error("=" * 60)
            
            # Skicka felnotifiering
            error_message = f"""
Remissorterare misslyckades!

Tidpunkt: {self.start_time}
Varaktighet: {duration}
Fel: {e}

Loggfil: {log_file}
            """
            
            self.send_email_notification(
                "Remissorterare - Fel",
                error_message
            )
    
    def cleanup(self):
        """Rensar upp efter körning"""
        try:
            # Ta bort gamla loggfiler (äldre än 30 dagar)
            log_dir = Path(".")
            for log_file in log_dir.glob("scheduled_run_*.log"):
                if log_file.stat().st_mtime < (datetime.now().timestamp() - 30 * 24 * 3600):
                    log_file.unlink()
                    logger.info(f"Tog bort gammal loggfil: {log_file}")
        except Exception as e:
            logger.warning(f"Kunde inte rensa gamla loggfiler: {e}")


def main():
    """Huvudfunktion för schemalagd körning"""
    
    # E-postkonfiguration (valfritt)
    email_config = {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'username': os.getenv('EMAIL_USERNAME'),
        'password': os.getenv('EMAIL_PASSWORD'),
        'from_email': os.getenv('FROM_EMAIL'),
        'to_email': os.getenv('TO_EMAIL')
    }
    
    # Kör endast om e-post är konfigurerat
    if not all([email_config['username'], email_config['password'], 
                email_config['from_email'], email_config['to_email']]):
        email_config = None
        logger.info("E-postnotifiering är inte konfigurerad")
    
    # Skapa och kör schemalagd körning
    runner = ScheduledRunner(email_config)
    
    try:
        runner.run()
    finally:
        runner.cleanup()
    
    # Returnera exit-kod baserat på framgång
    return 0 if runner.success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
