# Déploiement de production sur Render

## 1. Préparer les services

1. Pousser à GitHub la racine du dépôt avec `render.yaml`, `Backend/`, `Frontend/` et `REFERENCE/logo.jpeg`.
2. Dans Render, choisir **New + → Blueprint**, connecter le dépôt et la branche `main`, puis déployer le Blueprint.
3. Le Blueprint crée l’API FastAPI (Docker), deux Cron Jobs (expiration horaire et relances quotidiennes), le frontend statique, PostgreSQL et le disque persistant des PDF. Il ne crée ni worker permanent ni Redis/Key Value.
4. Avant le premier déploiement, renseigner les variables `sync: false` de l’API (voir ci-dessous). Render exécute `alembic upgrade head` en pré-déploiement de l’API. Le Cron vérifie que la base est à la dernière révision Alembic avant de lancer l’expiration ; il échoue explicitement et ne traite aucun devis si les migrations ne sont pas à jour.

Ne pas lancer `docker compose` pour ce dépôt : `docker-compose.yml` est vide. Render déploie les services déclarés dans `render.yaml` et le backend est construit avec `Backend/Dockerfile` depuis la racine du dépôt.

## 2. Variables à configurer dans Render

Le Blueprint relie automatiquement PostgreSQL, l’API, le Cron et le frontend. Vous configurez vous-même les secrets et les informations d’entreprise dans **proquote-erp-api → Environment** (ou dans les champs demandés par Render pendant la création du Blueprint). Ne collez jamais ces valeurs dans GitHub.

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

Les variables SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`) et `COMPANY_NAME` doivent aussi être configurées dans l’environnement du Cron `proquote-erp-payment-reminders` ; Render ne copie pas automatiquement les variables d’un service à l’autre. `SMTP_PASSWORD` doit rester une variable privée.

Pour `COMPANY_ADDRESS`, `COMPANY_CONTACTS` et `COMPANY_BANK_DETAILS`, coller les valeurs exactes fournies par l’entreprise. Dans les coordonnées bancaires, saisir les champs bancaires ci-dessus, sans montant en FCFA. Séparer chaque ligne par un retour à la ligne ou par `\n`. Ces informations sont injectées au rendu du PDF depuis l’environnement ; ne pas les ajouter au code, au dépôt ou aux variables `VITE_*`.

Configuration manuelle, dans cet ordre :

1. Connecter le dépôt à Render et examiner les services proposés par le Blueprint.
2. Renseigner les variables `sync: false` dans **proquote-erp-api → Environment**. `SECRET_KEY` est générée par Render ; ne pas la remplacer par une valeur partagée.
3. Enregistrer les variables. Laisser `DATABASE_URL` liée à PostgreSQL ; elle ne doit pas être saisie à la main. Aucun `REDIS_URL` n’est nécessaire.
4. Déployer l’API et attendre la fin du pré-déploiement Alembic ainsi que le contrôle de santé. Configurer les variables SMTP privées dans le Cron des relances avant de l’activer.
5. Si l’URL du frontend diffère de celle indiquée dans le Blueprint, corriger `ALLOWED_ORIGINS` avec son origine HTTPS exacte avant de déployer.

Le plan PostgreSQL `basic-1gb` est un plan propre à Render Postgres, contrairement aux plans compute de l’API et des Cron. Si `proquote-erp-db` existe déjà, comparer son plan/capacité et vérifier les sauvegardes avant toute synchronisation du Blueprint : un changement de plan peut provoquer une indisponibilité et un coût différent. Ne pas supprimer ni remplacer la base pour résoudre une erreur de Blueprint.

`DATABASE_URL` est reliée automatiquement à PostgreSQL. Le Cron reçoit la même connexion directement depuis cette base et n’a pas besoin des secrets SMTP ou d’authentification. `PDF_STORAGE_PATH` doit rester `/var/data/pdfs` : les PDF sont enregistrés sur le disque persistant Render, monté sur l’API. `COMPANY_LOGO_URL` doit rester `/app/REFERENCE/logo.jpeg`.

Si le nom de domaine Render du frontend change, mettre à jour `ALLOWED_ORIGINS` avec cette origine exacte. `VITE_API_URL` est reliée à l’URL publique HTTPS de l’API ; le frontend ajoute lui-même `/api/v1`. Ne pas y mettre de secret.

## 3. Vérifier le déploiement

1. Attendre que PostgreSQL, l’API et le frontend soient opérationnels, puis confirmer que le pré-déploiement des migrations Alembic s’est terminé sans erreur. Vérifier **proquote-erp-expire-quotations** (horaire `0 * * * *`, chaque heure UTC) et **proquote-erp-payment-reminders** (horaire `0 8 * * *`, chaque jour à 08:00 UTC).
2. Ouvrir `https://<url-api>/health` : la réponse attendue contient `status: ok` et `database: ok`. Si PostgreSQL est indisponible, l’API doit répondre HTTP 503.
3. Ouvrir le frontend, se connecter et vérifier les appels API. Créer un devis de test, générer puis télécharger son PDF ; vérifier l’adresse, les contacts et toutes les coordonnées bancaires. Le nom du PDF doit suivre la référence du devis, par exemple `001#10-10-2026.pdf`.
4. Vérifier les logs des deux Cron après leur déclenchement : le premier indique le nombre de devis expirés et le second le nombre de relances envoyées. Vérifier également **/system/tasks-health** avec un compte administrateur.
5. Vérifier l’envoi SMTP uniquement après avoir configuré le fournisseur et ses identifiants.
6. Créer le premier administrateur depuis le Shell du service API avec `python -m app.bootstrap_admin` et suivre les invites interactives. Ne pas placer le mot de passe dans le dépôt.

Le disque `/var/data` des PDF est persistant pour l’API, mais il ne remplace pas une sauvegarde. PostgreSQL payant inclut des sauvegardes et une restauration à un instant donné selon la rétention du plan Render ; vérifier dans le Dashboard la rétention réellement applicable au plan choisi et effectuer périodiquement un export chiffré indépendant ainsi qu’un test de restauration. Les migrations créent/évoluent le schéma mais ne recopient pas les données de `test.db` : prévoir séparément toute reprise de données avant la mise en production.

## 4. Scénarios de coût mensuel indicatif

Les montants ci-dessous sont en USD, avant taxes et dépassements éventuels. Les plans de compute ont conservé leurs tarifs malgré le changement d’identifiants Render en août 2026. Vérifier le montant final dans le Dashboard avant toute validation.

| Scénario | Architecture et estimation | Limites / risques |
| --- | --- | --- |
| **1 — coût minimal (0 $)** | Frontend statique gratuit, API sur `free`, PostgreSQL gratuit. | Démonstration temporaire uniquement, pas production : API arrêtée après 15 min sans trafic (réveil pouvant prendre environ 1 min), 750 heures gratuites partagées par espace/mois, aucun disque persistant, PDF perdus au redémarrage, Cron non gratuit, SMTP sortant bloqué sur les ports usuels 25/465/587. PostgreSQL gratuit limité à 1 Go, sans sauvegarde, expire après 30 jours ; après 14 jours de grâce sans passage en payant, Render supprime la base et ses données. Exporter les données et PDF régulièrement. Ce scénario n’est pas compatible avec le Blueprint complet actuel ni avec une disponibilité fiable. |
| **2 — recommandé** | API `0.5c-512mb` (~7 $), PostgreSQL `basic-1gb` (~19 $), disque PDF de 1 Go (~0,25 $), deux Cron (au minimum ~1 $ chacun), frontend statique (0 $) : **environ 28,25 $/mois minimum**. | Cron facturés à l’usage avec un minimum de 1 $ par service ; coûts sensibles à la durée d’exécution, taxes, consommation réseau, sauvegardes externes et changements tarifaires. PostgreSQL payant fournit les sauvegardes et le PITR selon les conditions du plan ; vérifier la rétention dans le Dashboard. |

Références officielles : [plans de compute](https://render.com/docs/compute-plans), [limites du gratuit](https://render.com/docs/free), [Cron Jobs et facturation](https://render.com/docs/cronjobs), [stockage persistant](https://render.com/docs/disks), [tarifs Render](https://render.com/pricing). Le scénario recommandé conserve les PDF sur disque et les deux tâches périodiques ; il n’ajoute pas Redis car aucun broker distribué n’est utilisé par ces jobs.

## 5. Déploiement automatique GitHub (facultatif)

Le workflow `.github/workflows/render-deploy.yml` déclenche un déploiement Render à chaque push sur `main` ou `master`. Dans Render, créer un **Deploy Hook**, puis enregistrer son URL dans GitHub sous **Settings → Secrets and variables → Actions** avec le nom `RENDER_DEPLOY_HOOK_URL`. Ne pas écrire cette URL dans le dépôt.

Ce workflow est facultatif. Sans `RENDER_DEPLOY_HOOK_URL`, son exécution se termine volontairement sans déclencher Render ; le statut GitHub « success » ne signifie alors pas que l’application a été déployée. Pour configurer et lancer le premier déploiement manuellement, utiliser le Blueprint dans le Dashboard Render.

-----------------------------
## Rappel avant le premier déploiement

Dans Render, choisissez **New + → Blueprint**, connectez `ZANA-JB/proquote-erp` et sélectionnez `main`. Renseignez les informations d’entreprise et, si l’envoi d’e-mails est nécessaire, les variables SMTP décrites plus haut. Laissez Render générer `SECRET_KEY`, gardez la liaison PostgreSQL automatique et vérifiez `ALLOWED_ORIGINS`.

Le Blueprint ne crée ni Redis ni worker : il crée les deux Cron décrits ci-dessus. Le déploiement Render n’a pas encore été effectué ; vérifiez `/health`, les migrations, les deux Cron, les PDF et la création du premier administrateur dans le Dashboard avant toute utilisation réelle. Le workflow GitHub peut afficher « success » sans déployer si `RENDER_DEPLOY_HOOK_URL` n’est pas configuré.
--------------------------------------------
