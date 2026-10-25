# Système de Gestion des Cotations (backend)

Ce backend FastAPI gère les devis, l'envoi de PDF, la journalisation, les rappels d'impayés et le dashboard.

## Configuration

Copiez `.env.example` vers `.env` et ajustez les valeurs.

- `DATABASE_URL`: URL de la base de données PostgreSQL de production.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: configuration SMTP.
- `SMTP_PORT=587` pour STARTTLS.
- `SMTP_PORT=465` pour SSL/TLS direct.
- `MAIL_FROM`: adresse de l'expéditeur.
  
Pour les essais, utilisez uniquement un serveur SMTP de test ou une configuration explicitement autorisée. Aucun courriel réel n'est nécessaire pour exécuter les tests automatisés. Ne stockez pas de secrets dans le dépôt. Définissez une `SECRET_KEY` sûre avant toute mise en production.
- `ALLOWED_ORIGINS`: liste d'origines séparées par des virgules pour CORS.
- `PDF_STORAGE_PATH`: emplacement de génération des PDF.

## Tâches planifiées et relances

Les tâches Celery restent utilisées par les scripts de jobs, mais ni worker,
ni Redis/Key Value, ni Celery Beat ne sont nécessaires au Blueprint Render.
Celery utilise le broker mémoire local ; il ne doit donc pas servir de file
inter-processus en production. Deux Cron Render exécutent directement les tâches :
expiration horaire et relances de paiement quotidiennes à 08:00 UTC. Chaque job
refuse de s'exécuter si les migrations ne sont pas à jour. Les relances exigent
une configuration SMTP privée dans l'environnement du Cron.

## API

Toutes les routes sont préfixées par `/api/v1/`.

- Auth: `/api/v1/auth`
- Utilisateurs: `/api/v1/users`
- Devis: `/api/v1/quotations`
- Articles: `/api/v1/quotations/{quotation_id}/articles`
- Dashboard: `/api/v1/dashboard`
- Rappels: `/api/v1/quotations/{quotation_id}/reminders` et `/api/v1/reminders`

La documentation Swagger est disponible sur `/docs`.

## Déploiement Render

Le fichier `render.yaml` à la racine déclare un frontend statique, une API Docker,
PostgreSQL, un disque persistant pour les PDF et deux Cron périodiques. Il ne
déclare ni Redis/Key Value ni worker Celery. Le déploiement Render n'a pas été
réalisé ou confirmé.

- Render exécute `alembic upgrade head` comme commande de pré-déploiement de l'API,
  puis l'image démarre Uvicorn sur `0.0.0.0:$PORT`.
- Le disque persistant Render est monté sur `/var/data`; les PDF sont enregistrés sous `/var/data/pdfs`.
- Le Cron horaire appelle `python -m app.tasks.run_expiration_job`. Le Cron quotidien
  appelle `python -m app.tasks.run_payment_reminders_job`.
- Après le premier déploiement, ouvrir le Shell du service API et lancer `python -m app.bootstrap_admin` pour créer le premier administrateur. Le mot de passe est saisi de façon interactive et n'est pas conservé dans le dépôt.
- Renseigner SMTP et `COMPANY_BANK_DETAILS` dans les variables privées du Dashboard Render, jamais dans le dépôt.
- `VITE_RENDER_DEPLOYED` reste à `false` dans le blueprint. Le passer à `true` et redéployer le frontend uniquement après vérification que l'API, PostgreSQL et le frontend sont réellement opérationnels sur Render.
- Les migrations créent le schéma PostgreSQL mais ne transfèrent pas les lignes de `test.db`. Toute reprise de données existantes doit être planifiée et vérifiée séparément avant la bascule.
