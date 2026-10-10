# Déploiement de production sur Render

## 1. Préparer les services

1. Pousser à GitHub la racine du dépôt avec `render.yaml`, `Backend/`, `Frontend/` et `REFERENCE/logo.jpeg`.
2. Dans Render, choisir **New + → Blueprint**, connecter le dépôt et la branche `main`, puis déployer le Blueprint.
3. Le Blueprint crée l’API FastAPI (Docker), le worker Celery, le frontend statique, PostgreSQL, Redis/Key Value et le disque persistant des PDF.
4. Avant le premier déploiement, renseigner les variables `sync: false` de l’API (voir ci-dessous). Le service API exécute les migrations Alembic au démarrage. Le worker et le frontend récupèrent leurs variables liées depuis l’API.

Ne pas lancer `docker compose` pour ce dépôt : `docker-compose.yml` est vide. Render déploie les services déclarés dans `render.yaml` et le backend est construit avec `Backend/Dockerfile` depuis la racine du dépôt.

## 2. Variables à configurer dans Render

Le Blueprint crée les services et relie automatiquement PostgreSQL, Key Value, l’API et le frontend. Vous configurez vous-même les secrets et les informations d’entreprise dans **proquote-erp-api → Environment** (ou dans les champs demandés par Render pendant la création du Blueprint). Ne collez jamais ces valeurs dans GitHub.

| Variable | Valeur à renseigner |
| --- | --- |
| `SECRET_KEY` | Générer une clé aléatoire d’au moins 32 caractères. Si Render l’a déjà générée via le Blueprint, la conserver. |
| `ALLOWED_ORIGINS` | Origine HTTPS exacte du frontend, sans chemin, par exemple `https://proquote-erp-frontend.onrender.com`. |
| `SMTP_HOST` | Serveur SMTP fourni par l’entreprise ou le fournisseur de messagerie. |
| `SMTP_PORT` | `587` avec STARTTLS, ou `465` avec SSL/TLS. |
| `SMTP_USER` | Identifiant SMTP. |
| `SMTP_PASSWORD` | Mot de passe ou jeton SMTP. |
| `MAIL_FROM` | Adresse expéditrice autorisée par le serveur SMTP. |
| `COMPANY_NAME` | Nom de l’entreprise à afficher sur les devis et dans les e-mails. |
| `COMPANY_ADDRESS` | Adresse, puis RCCM et CC tels que fournis par l’entreprise. |
| `COMPANY_CONTACTS` | Téléphone et e-mail à afficher sur les devis. |
| `COMPANY_BANK_DETAILS` | Coordonnées bancaires uniquement : code banque, code guichet, domiciliation, numéro de compte, clé RIB, BIC et IBAN. Ne pas inclure de montant (en particulier « 200 FCFA »). |

Pour `COMPANY_ADDRESS`, `COMPANY_CONTACTS` et `COMPANY_BANK_DETAILS`, coller les valeurs exactes fournies par l’entreprise. Dans les coordonnées bancaires, saisir les champs bancaires ci-dessus, sans montant en FCFA. Séparer chaque ligne par un retour à la ligne ou par `\n`. Ces informations sont injectées au rendu du PDF depuis l’environnement ; ne pas les ajouter au code, au dépôt ou aux variables `VITE_*`.

Configuration manuelle, dans cet ordre :

1. Connecter le dépôt à Render et examiner les services proposés par le Blueprint.
2. Renseigner les variables `sync: false` dans **proquote-erp-api → Environment**. `SECRET_KEY` est générée par Render ; ne pas la remplacer par une valeur partagée.
3. Enregistrer les variables. Laisser `DATABASE_URL` et `REDIS_URL` liées aux services créés par le Blueprint ; elles ne doivent pas être saisies à la main.
4. Déployer l’API et attendre son contrôle de santé avant de vérifier le frontend et le worker.
5. Si l’URL du frontend diffère de celle indiquée dans le Blueprint, corriger `ALLOWED_ORIGINS` avec son origine HTTPS exacte avant de déployer.

`DATABASE_URL` et `REDIS_URL` sont reliées automatiquement aux services PostgreSQL et Key Value du Blueprint. `PDF_STORAGE_PATH` doit rester `/var/data/pdfs` : les PDF sont enregistrés sur le disque persistant Render. `COMPANY_LOGO_URL` doit rester `/app/REFERENCE/logo.jpeg`.

Si le nom de domaine Render du frontend change, mettre à jour `ALLOWED_ORIGINS` avec cette origine exacte. `VITE_API_URL` est reliée à l’URL publique HTTPS de l’API ; le frontend ajoute lui-même `/api/v1`. Ne pas y mettre de secret.

## 3. Vérifier le déploiement

1. Attendre que l’API, le worker, le frontend, Key Value et PostgreSQL soient opérationnels et que le dernier déploiement soit terminé sans erreur.
2. Ouvrir `https://<url-api>/health` : la réponse attendue contient `status: ok` et `database: ok`.
3. Ouvrir le frontend, se connecter et vérifier les appels API. Créer un devis de test, générer puis télécharger son PDF ; vérifier l’adresse, les contacts et toutes les coordonnées bancaires. Le nom du PDF doit suivre la référence du devis, par exemple `001#10-10-2026.pdf`.
4. Vérifier l’envoi SMTP uniquement après avoir configuré le fournisseur et ses identifiants.
5. Créer le premier administrateur depuis le Shell du service API avec `python -m app.bootstrap_admin` et suivre les invites interactives. Ne pas placer le mot de passe dans le dépôt.

Le déploiement Render réel ne peut être confirmé qu’après cette vérification dans le compte Render. Les migrations créent le schéma mais ne recopient pas les données de `test.db` : prévoir séparément toute reprise de données avant la mise en production.

## 4. Déploiement automatique GitHub (facultatif)

Le workflow `.github/workflows/render-deploy.yml` déclenche un déploiement Render à chaque push sur `main` ou `master`. Dans Render, créer un **Deploy Hook**, puis enregistrer son URL dans GitHub sous **Settings → Secrets and variables → Actions** avec le nom `RENDER_DEPLOY_HOOK_URL`. Ne pas écrire cette URL dans le dépôt.

Ce workflow est facultatif. Sans `RENDER_DEPLOY_HOOK_URL`, son exécution se termine volontairement sans déclencher Render ; le statut GitHub « success » ne signifie alors pas que l’application a été déployée. Pour configurer et lancer le premier déploiement manuellement, utiliser le Blueprint dans le Dashboard Render.