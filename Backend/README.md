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

## TVA et modalités de règlement des devis

Le montant persisté `total_amount` reste le total HT afin de conserver la
compatibilité avec les données et rapports existants. La TVA est choisie par
devis : soit « sans TVA », soit un code et un taux saisis par l’utilisateur.
Aucun code ni taux n’est prérempli. Le montant de TVA est calculé sur le total
HT, arrondi au centime, puis ajouté pour obtenir le total TTC affiché dans le
PDF et l’API. Les devis déjà enregistrés sont migrés avec le régime explicite
« sans TVA », suivant la confirmation de l’organisation.

Le mode de règlement et les modalités/échéances sont facultatifs et enregistrés
avec le devis. Ils ne sont affichés sur le PDF que lorsqu’ils sont renseignés.
`payment_reminders.due_date` reste une date de relance et n’est pas utilisée
comme échéance commerciale du devis.

## Déploiement Render

Le fichier `render.yaml` à la racine déclare un frontend statique, une API Docker,
PostgreSQL, un disque persistant pour les PDF et deux Cron périodiques. Il ne
déclare ni Redis/Key Value ni worker Celery. Le 25 octobre 2026, un contrôle GET
public a reçu HTTP 200 sur `/health` (base de données signalée opérationnelle) et sur
le frontend. Cela ne confirme pas que le commit courant est déployé ni que les Cron,
SMTP ou la génération PDF en production fonctionnent.

- Render exécute `alembic upgrade head` comme commande de pré-déploiement de l'API,
  puis l'image démarre Uvicorn sur `0.0.0.0:$PORT`.
- Le disque persistant Render est monté sur `/var/data`; les PDF sont enregistrés sous `/var/data/pdfs`.
- Le Cron horaire appelle `python -m app.tasks.run_expiration_job`. Le Cron quotidien
  appelle `python -m app.tasks.run_payment_reminders_job`.
- Dans le Shell du service API Render (conteneur Linux, pas PowerShell Windows), lancer `python -m app.bootstrap_admin`. Le script crée le premier administrateur si aucun n'existe. S'il existe déjà un compte administrateur à l'adresse saisie, il réinitialise uniquement son mot de passe, conserve son identifiant et ses données liées, puis invalide ses sessions actives. Confirmer l'adresse exacte à l'invite ; le mot de passe est saisi sans affichage. Si un administrateur existe sous une autre adresse, utiliser cette adresse exacte. Le script ne supprime aucun compte ni aucune donnée métier.
- Renseigner SMTP et `COMPANY_BANK_DETAILS` dans les variables privées du Dashboard Render, jamais dans le dépôt.
- Les migrations créent le schéma PostgreSQL mais ne transfèrent pas les lignes de `test.db`. Toute reprise de données existantes doit être planifiée et vérifiée séparément avant la bascule.
