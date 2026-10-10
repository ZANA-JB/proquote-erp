# Système de Gestion des Cotations (backend)

Ce backend FastAPI gère les devis, l'envoi de PDF, la journalisation, les rappels d'impayés et le dashboard.

## Configuration

Copiez `.env.example` vers `.env` et ajustez les valeurs.

- `DATABASE_URL`: URL de la base de données PostgreSQL de production.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`: configuration SMTP.
- `SMTP_PORT=587` pour STARTTLS.
- `SMTP_PORT=465` pour SSL/TLS direct.
- `MAIL_FROM`: adresse de l'expéditeur.
  
Note: pour les tests, vous pouvez temporairement utiliser une adresse personnelle, mais en production remplacez ces valeurs par celles fournies par l'entreprise. Assurez-vous également de définir `SECRET_KEY` dans `.env` avant toute mise en production.
- `ALLOWED_ORIGINS`: liste d'origines séparées par des virgules pour CORS.
- `PDF_STORAGE_PATH`: emplacement de génération des PDF.

## Tâches Celery

- Démarrer un worker :
  ```bash
  cd Backend
  celery -A app.tasks.celery_app worker --loglevel=info
  ```
- Démarrer le planificateur (beat) :
  ```bash
  cd Backend
  celery -A app.tasks.celery_app beat --loglevel=info
  ```
- Lancer worker et beat ensemble en production :
  ```bash
  cd Backend
  celery -A app.tasks.celery_app worker --beat --loglevel=info
  ```

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

Le fichier `render.yaml` à la racine déclare le frontend statique, l'API Docker, PostgreSQL, Render Key Value et le worker Celery. Le dépôt connecté à Render doit contenir ensemble `Backend/`, `Frontend/` et `REFERENCE/`.

- L'image API exécute `alembic upgrade head`, puis démarre Uvicorn sur `0.0.0.0:$PORT`.
- Le disque persistant Render est monté sur `/var/data`; les PDF sont enregistrés sous `/var/data/pdfs`.
- Le worker Celery utilise Render Key Value pour les rappels planifiés et l'expiration des devis.
- Après le premier déploiement, ouvrir le Shell du service API et lancer `python -m app.bootstrap_admin` pour créer le premier administrateur. Le mot de passe est saisi de façon interactive et n'est pas conservé dans le dépôt.
- Renseigner SMTP et `COMPANY_BANK_DETAILS` dans les variables privées du Dashboard Render, jamais dans le dépôt.
- `VITE_RENDER_DEPLOYED` reste à `false` dans le blueprint. Le passer à `true` et redéployer le frontend uniquement après vérification que l'API, PostgreSQL et le frontend sont réellement opérationnels sur Render.
- Les migrations créent le schéma PostgreSQL mais ne transfèrent pas les lignes de `test.db`. Toute reprise de données existantes doit être planifiée et vérifiée séparément avant la bascule.
