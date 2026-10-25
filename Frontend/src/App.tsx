// Centralise les écrans, appels API et actions des différents profils.
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import logo from './assets/LOGO.jpeg'
import './App.css'

const configuredApiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
const securedApiUrl = configuredApiUrl.startsWith('http') ? configuredApiUrl : `https://${configuredApiUrl}`
const trimmedApiUrl = securedApiUrl.replace(/\/$/, '')
const API_BASE_URL = trimmedApiUrl.endsWith('/api/v1') ? trimmedApiUrl : `${trimmedApiUrl}/api/v1`
let activeAccessToken: string | null = null

async function readApiResponse<T>(response: Response, context: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null
    const detail = typeof payload?.detail === 'string' ? payload.detail : `${context} (HTTP ${response.status}).`
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

type CurrentView = 'login' | 'accessRequest' | 'adminDashboard' | 'legal' | 'privacy' | 'support'
type AdminPage = 'dashboard' | 'devis' | 'users' | 'roles' | 'reports' | 'settings' | 'help'

const getInitialCurrentView = (): CurrentView => {
  const path = window.location.pathname
  if (path === '/mentions-legales') return 'legal'
  if (path === '/confidentialite') return 'privacy'
  if (path === '/support-technique') return 'support'
  return 'login'
}

const getRolePresentation = (role: string) => {
  if (role === 'ADMIN') return { className: 'admin', label: 'Admin' }
  if (role === 'RESPONSABLE') return { className: 'manager', label: 'Responsable' }
  return { className: 'employee', label: 'Collaborateur' }
}

type User = {
  id: string
  email: string
  full_name?: string | null
  avatar_url?: string | null
  role: string
  is_active: boolean
  created_at?: string
}

type QuotationItem = {
  id: string
  reference: string
  client_name: string
  creation_date: string
  total_amount: number
  status: string
  purchase_indicator: string
}

type ArticleLine = {
  designation: string
  quantity: number
  unit: string
  unit_price: number
  line_total: number
}

type QuotationFormState = {
  client_name: string
  client_email: string
  client_address: string
  client_reference: string
  validity_date: string
  delivery_duration: string
  incoterm: string
  special_conditions: string
  vat_mode: string
  vat_code: string
  vat_rate: string
  payment_method: string
  payment_terms: string
  articles: ArticleLine[]
}

const defaultArticleLine: ArticleLine = {
  designation: '',
  quantity: 1,
  unit: '',
  unit_price: 0,
  line_total: 0,
}

const defaultQuotationForm: QuotationFormState = {
  client_name: '',
  client_email: '',
  client_address: '',
  client_reference: '',
  validity_date: new Date().toISOString().slice(0, 10),
  delivery_duration: '',
  incoterm: '',
  special_conditions: '',
  vat_mode: '',
  vat_code: '',
  vat_rate: '',
  payment_method: '',
  payment_terms: '',
  articles: [{ ...defaultArticleLine }],
}

type QuotationChartPoint = {
  label: string
  value: number
}

type PaginatedQuotationResponse = {
  total: number
  skip: number
  limit: number
  items: QuotationItem[]
}

type DashboardSummary = {
  total_quotations: number
  sent_count: number
  accepted_count: number
  refused_count: number
  expired_count: number
  draft_count: number
  total_amount: number
  conversion_rate: number
}

type AccessRequestItem = {
  id: string
  nomComplet: string
  email: string
  profilSouhaite: string
  status: 'EN_ATTENTE' | 'ACCEPTEE' | 'REFUSEE'
  created_at: string
}

type AccessFormState = {
  nomComplet: string
  email: string
  motDePasse: string
  profilSouhaite: string
}

const defaultAccessForm: AccessFormState = {
  nomComplet: '',
  email: '',
  motDePasse: '',
  profilSouhaite: '',
}

const defaultSummary: DashboardSummary = {
  total_quotations: 0,
  sent_count: 0,
  accepted_count: 0,
  refused_count: 0,
  expired_count: 0,
  draft_count: 0,
  total_amount: 0,
  conversion_rate: 0,
}

const STANDARD_INCOTERM_VALUES = ['DDP', 'EXW', 'CPT', 'CFR'] as const

const getIncotermSelectValue = (value?: string | null) => {
  const normalized = String(value ?? '').trim().toUpperCase()
  if (!normalized) return 'AUTRE'
  if (STANDARD_INCOTERM_VALUES.includes(normalized as (typeof STANDARD_INCOTERM_VALUES)[number])) {
    return normalized
  }
  if (normalized === 'EXW / EXWORK') return 'EXW'
  return 'AUTRE'
}

const getCustomIncotermValue = (value?: string | null) => {
  const normalized = String(value ?? '').trim().toUpperCase()
  if (!normalized) return ''
  if (STANDARD_INCOTERM_VALUES.includes(normalized as (typeof STANDARD_INCOTERM_VALUES)[number])) {
    return ''
  }
  if (normalized === 'EXW / EXWORK') return ''
  return String(value ?? '').trim()
}

const adminPageLabels: Record<AdminPage, string> = {
  dashboard: "Vue d'ensemble Admin",
  devis: 'Devis',
  users: 'Utilisateurs',
  roles: 'Rôle',
  reports: 'Rapport',
  settings: 'Paramètres',
  help: 'Aide',
}

const adminPageIcons: Record<AdminPage, string> = {
  dashboard: 'dashboard',
  devis: 'description',
  users: 'group',
  roles: 'admin_panel_settings',
  reports: 'analytics',
  settings: 'settings',
  help: 'help',
}

const formatDateTime = (value?: string) => {
  if (!value) return 'Aucune donnée disponible'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Aucune donnée disponible'

  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

const normalizeText = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')

const matchesQuery = (query: string, ...values: Array<string | number | null | undefined>) => {
  const search = normalizeText(query)
  if (!search) return true

  return values.some((value) => normalizeText(String(value ?? '')).includes(search))
}

const formatCurrency = (value: number) =>
  `${new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value || 0)} FCFA`

const formatPercent = (value: number) => `${Math.round((Number.isFinite(value) ? value : 0) * 100)}%`

const getRoleLandingPage = (role: string): AdminPage => {
  if (role === 'ADMIN' || role === 'RESPONSABLE') return 'dashboard'
  return 'devis'
}

const getInitialAdminPage = (role: string): AdminPage => {
  const path = window.location.pathname
  if (path === '/parametres') return 'settings'
  if (path === '/aide') return 'help'
  return getRoleLandingPage(role)
}

const getRoleClassName = (role?: string) => {
  if (role === 'ADMIN') return 'admin'
  if (role === 'RESPONSABLE') return 'manager'
  return 'employee'
}

const getRoleLabel = (role?: string) => {
  const normalized = String(role ?? '').trim().toUpperCase()

  if (normalized === 'ADMIN') return 'Administrateur'
  if (normalized === 'RESPONSABLE') return 'Manager'
  if (normalized === 'COLLABORATEUR') return 'Employé / Commercial'

  return role || 'Rôle inconnu'
}

const getRequestStatusPresentation = (status?: string) => {
  const normalized = String(status || '').trim().toUpperCase()

  if (normalized === 'EN_ATTENTE') {
    return { label: 'En attente', className: 'pending' }
  }

  if (normalized === 'ACCEPTEE') {
    return { label: 'Acceptée', className: 'accepted' }
  }

  if (normalized === 'REFUSEE') {
    return { label: 'Refusée', className: 'rejected' }
  }

  return { label: normalized || 'Inconnu', className: 'other' }
}

const getChartMonthIndex = (label?: string | null) => {
  const normalized = String(label || '').trim()
  const parts = normalized.split('-')
  if (parts.length < 2) {
    return null
  }

  const month = Number(parts[1])
  if (!Number.isFinite(month) || month < 1 || month > 12) {
    return null
  }

  return month - 1
}

const monthLabels = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aout', 'Sep', 'Oct', 'Nov', 'Dec']

const getChartYearFromSeries = (seriesData: QuotationChartPoint[]) => {
  const unmatchedYear = seriesData
    .map((point) => point.label?.split('-')[0])
    .find((year) => /^\d{4}$/.test(String(year ?? '')))

  const parsedYear = Number(unmatchedYear)
  return Number.isFinite(parsedYear) ? parsedYear : new Date().getFullYear()
}

const buildMonthlyChartSeries = (seriesData: QuotationChartPoint[]) => {
  const monthMap = new Map<number, number>()
  for (let index = 0; index < 12; index += 1) {
    monthMap.set(index, 0)
  }

  seriesData.forEach((point) => {
    const monthIndex = getChartMonthIndex(point.label)
    if (monthIndex !== null) {
      monthMap.set(monthIndex, Number(point.value) || 0)
    }
  })

  const series = monthLabels.map((label, index) => ({
    label,
    value: monthMap.get(index) || 0,
  }))

  const maximumValue = Math.max(...series.map((point) => point.value), 0)
  const normalizedMax = maximumValue > 0 ? Math.ceil(maximumValue * 1.1) : 5

  return { series, normalizedMax, year: getChartYearFromSeries(seriesData) }
}

function LegalNoticesPage() {
  return (
    <main className="legal-page-shell">
      <header className="legal-page-topbar">
        <a className="legal-brand" href="/" aria-label="Retour à l’accueil ProQuote ERP">
          <img src={logo} alt="Trident Oil Services" />
          <span>ProQuote ERP</span>
        </a>
        <a className="legal-back-link" href="/">
          <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
          Retour à l’accueil
        </a>
      </header>

      <div className="legal-page-content">
        <div className="legal-page-heading">
          <p>PROQUOTE ERP</p>
          <h1>Mentions légales</h1>
          <span>Informations relatives à l’éditeur et à l’hébergement du service.</span>
        </div>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Éditeur</h2>
          </div>
          <p>
            L’identité juridique de l’éditeur, sa raison sociale, sa forme juridique, son adresse,
            ses coordonnées, ses numéros d’immatriculation et le responsable de publication ne
            sont pas confirmés par les sources techniques auditées. Ces informations doivent être
            fournies et validées par l’organisation éditrice.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Hébergement</h2>
          </div>
          <p>
            <strong>Hébergement : Render.</strong>
          </p>
        </section>

        <p className="privacy-note">
          La page <a href="/confidentialite">Confidentialité</a> décrit les éléments techniques constatés.
        </p>
      </div>
    </main>
  )
}

function PrivacyPage() {
  const privacyContactEmail = 'tridentoilservices@gmail.com'

  return (
    <main className="legal-page-shell privacy-page-shell">
      <header className="legal-page-topbar">
        <a className="legal-brand" href="/" aria-label="Retour à l’accueil ProQuote ERP">
          <img src={logo} alt="Trident Oil Services" />
          <span>ProQuote ERP</span>
        </a>
        <a className="legal-back-link" href="/">
          <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
          Retour à l’accueil
        </a>
      </header>

      <div className="legal-page-content">
        <div className="legal-page-heading">
          <p>PROTECTION DES DONNÉES</p>
          <h1>Confidentialité</h1>
          <span>Données et opérations effectuées par ProQuote ERP en production.</span>
        </div>

        <section className="legal-section privacy-intro-section">
          <div className="legal-section-heading">
            <h2>Portée</h2>
          </div>
          <p>
            Cette notice décrit les informations que l’application utilise pour gérer les accès,
            les demandes d’accès, les clients et les devis, ainsi que les opérations de PDF,
            d’envoi de devis et de suivi. Les champs collectés sont ceux nécessaires à ces
            fonctionnalités ; n’ajoutez pas de données personnelles qui ne sont pas utiles au
            traitement du devis ou à la gestion du compte.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Données utilisées</h2>
          </div>
          <div className="privacy-grid">
            <div className="privacy-block">
              <h3>Comptes et demandes d’accès</h3>
              <ul className="privacy-list">
                <li>Nom, adresse e-mail, rôle et état du compte</li>
                <li>Hash du mot de passe (le mot de passe en clair n’est pas stocké dans le modèle utilisateur)</li>
                <li>Avatar lorsqu’il est renseigné</li>
                <li>Pour une demande d’accès : nom, e-mail, profil souhaité, état, date et hash du mot de passe demandé</li>
              </ul>
            </div>
            <div className="privacy-block">
              <h3>Clients et devis</h3>
              <ul className="privacy-list">
                <li>Nom, e-mail, adresse et référence du client enregistrés dans le devis</li>
                <li>Référence et dates du devis, statut et montant</li>
                <li>Désignation des articles, quantités, unités, prix et conditions commerciales</li>
                <li>État payé/non payé et données de relance lorsque ces fonctionnalités sont utilisées</li>
              </ul>
            </div>
            <div className="privacy-block privacy-block-wide">
              <h3>Journaux et fichiers</h3>
              <ul className="privacy-list">
                <li>Journaux applicatifs d’actions : utilisateur, action, type et identifiant d’entité, date et détails associés</li>
                <li>Relances : devis concerné, date de référence calculée depuis sa validité, date d’envoi et état d’envoi</li>
                <li>PDF enregistrés sous le chemin configuré ; les avatars sont conservés comme valeur dans le compte utilisateur</li>
              </ul>
            </div>
          </div>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Traitements visibles dans le code</h2>
          </div>
          <ul className="privacy-list privacy-list-columns">
            <li>Authentification, gestion des rôles et demandes d’accès</li>
            <li>Création, consultation, modification et suppression de devis selon les permissions</li>
            <li>Calcul des montants, génération et téléchargement de PDF</li>
            <li>Envoi de devis et relances par e-mail via SMTP lorsque configuré</li>
            <li>Suivi de statut et données de paiement (état payé/non payé)</li>
            <li>Tableaux de bord, graphiques et historique d’actions</li>
          </ul>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Accès aux données</h2>
          </div>
          <div className="privacy-role-list">
            <p><strong>Administrateurs</strong> : routes d’administration des comptes et demandes d’accès.</p>
            <p><strong>Responsables</strong> : permissions métier et transitions de statut prévues par l’API.</p>
            <p><strong>Collaborateurs</strong> : les routes de devis filtrent leur accès à leurs propres devis.</p>
          </div>
          <p className="privacy-note">Ces rôles et contrôles sont définis dans les routes et dépendances de l’API.</p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Sécurité et protection</h2>
          </div>
          <ul className="privacy-list privacy-list-columns">
            <li>Jetons d’accès JWT avec expiration et version de révocation</li>
            <li>Hash des mots de passe avec PBKDF2-SHA256</li>
            <li>Contrôles de rôles et d’accès côté API, dont les routes PDF authentifiées</li>
            <li>Validation des entrées par les schémas API</li>
            <li>Le frontend conserve le jeton dans sessionStorage ; aucun cookie d’authentification n’est configuré dans le code audité</li>
          </ul>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Échanges par e-mail</h2>
          </div>
          <p>
            Le code peut envoyer un devis en pièce jointe PDF et des relances par e-mail à l’adresse
            enregistrée sur le devis. Ces envois utilisent le service SMTP configuré pour
            l’application. La page Support technique ouvre séparément un brouillon de message
            adressé à l’administrateur ; ce message n’est envoyé qu’après confirmation par
            l’utilisateur.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Hébergement et ressources externes</h2>
          </div>
          <ul className="privacy-list">
            <li>Les services de production déclarés dans Render comprennent l’API, le frontend statique, PostgreSQL, les tâches planifiées et le disque persistant utilisé pour les PDF.</li>
            <li>Le frontend charge les polices Inter et Material Symbols depuis Google Fonts.</li>
            <li>Les e-mails métier utilisent le serveur SMTP configuré dans l’environnement de production.</li>
            <li>Aucun modèle ou parcours d’authentification client final n’a été trouvé dans le code audité.</li>
          </ul>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Suppression, export et conservation</h2>
          </div>
          <p>
            Des routes de suppression administrative existent pour les comptes, les demandes
            d’accès et les devis, mais aucune procédure d’exercice des droits ni aucun export global
            n’est défini. La suppression d’un compte peut aussi être contrainte par les références
            conservées dans les journaux. L’application ne définit pas de purge automatique ni de
            durée de conservation pour les comptes, les devis et les PDF ; leur suppression suit
            les actions administratives et les règles de gestion des services d’hébergement.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Contact relatif aux données</h2>
          </div>
          <p>
            Pour toute question concernant les informations traitées dans ProQuote ERP, contactez
            l’administrateur de l’application à l’adresse{' '}
            <a href={`mailto:${privacyContactEmail}`}>{privacyContactEmail}</a>.
          </p>
        </section>

      </div>
    </main>
  )
}

function SupportPage() {
  const supportEmail = 'tridentoilservices@gmail.com'
  const supportUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${supportEmail}&su=${encodeURIComponent('Assistance technique — ProQuote ERP')}`

  return (
    <main className="legal-page-shell support-page-shell">
      <header className="legal-page-topbar">
        <a className="legal-brand" href="/" aria-label="Retour à l’accueil ProQuote ERP">
          <img src={logo} alt="Trident Oil Services" />
          <span>ProQuote ERP</span>
        </a>
        <a className="legal-back-link" href="/">
          <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
          Retour à l’accueil
        </a>
      </header>

      <div className="legal-page-content">
        <div className="legal-page-heading">
          <p>PROQUOTE ERP</p>
          <h1>Support technique</h1>
          <span>Repères pratiques pour les demandes d’accès, les devis et les PDF.</span>
        </div>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Créer un devis</h2>
          </div>
          <p>
            Connectez-vous, ouvrez la rubrique Devis puis choisissez « Nouveau devis ». Renseignez
            les informations du client, les dates et les conditions de livraison, puis ajoutez au
            moins une ligne avec sa désignation, sa quantité et son prix unitaire. Le total est
            calculé par l’application à partir des lignes du devis.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Télécharger un PDF</h2>
          </div>
          <p>
            Dans la rubrique Devis, utilisez l’action de téléchargement associée au devis. Le PDF
            reprend les informations enregistrées sur ce devis et les coordonnées de l’entreprise
            configurées pour l’application.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Connexion et accès</h2>
          </div>
          <p>
            Une demande d’accès doit être approuvée par un administrateur avant la connexion. Si
            votre compte est inactif ou si vous ne pouvez plus vous connecter, contactez
            l’administrateur de votre organisation par son canal habituel.
          </p>
        </section>

        <section className="legal-section">
          <div className="legal-section-heading">
            <h2>Contacter l’assistance</h2>
          </div>
          <p>
            Pour toute difficulté, contactez l’administrateur du système. Le message préparé inclut les informations utiles au diagnostic ; confirmez son contenu et envoyez-le depuis votre messagerie.
          </p>
          <a
            className="support-contact-button"
            href={supportUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span className="material-symbols-outlined" aria-hidden="true">mail</span>
            Contacter le support technique
          </a>
          <p>
            Adresse de l’administrateur : <a href={`mailto:${supportEmail}`}>{supportEmail}</a>
          </p>
        </section>
      </div>
    </main>
  )
}

function App() {
  const [currentView, setCurrentView] = useState<CurrentView>(getInitialCurrentView)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [storedAccessToken] = useState(() => sessionStorage.getItem('access_token'))
  const [isRestoringSession, setIsRestoringSession] = useState(Boolean(storedAccessToken))
  const [sessionError, setSessionError] = useState('')
  const isAuthenticated = Boolean(currentUser)

  useEffect(() => {
    let cancelled = false
    const token = storedAccessToken
    activeAccessToken = token

    if (!token) {
      return () => {
        cancelled = true
      }
    }

    const restoreSession = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: { Authorization: 'Bearer ' + token },
        })
        if (response.status === 401) {
          sessionStorage.removeItem('access_token')
          activeAccessToken = null
          setSessionError('Votre session a expiré. Veuillez vous reconnecter.')
          return
        }

        const user = await readApiResponse<User>(response, 'Impossible de vérifier la session.')
        if (!user.id || !user.role || !user.is_active) {
          throw new Error('Le profil reçu ne permet pas de rétablir une session valide.')
        }
        if (!cancelled) {
          setCurrentUser(user)
          setCurrentView((view) => view === 'login' ? 'adminDashboard' : view)
          setSessionError('')
        }
      } catch (error) {
        if (!cancelled) {
          setSessionError(error instanceof Error ? error.message : 'Impossible de vérifier la session.')
        }
      } finally {
        if (!cancelled) setIsRestoringSession(false)
      }
    }

    void restoreSession()
    return () => {
      cancelled = true
    }
  }, [storedAccessToken])

  const handleLogout = async (message = '') => {
    const token = activeAccessToken
    let logoutError = ''
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        })
      } catch {
        logoutError = 'La session locale a été fermée, mais le serveur n’a pas pu révoquer le jeton.'
      }
    }
    activeAccessToken = null
    sessionStorage.removeItem('access_token')
    setCurrentUser(null)
    setSessionError(message || logoutError)
    setCurrentView('login')
  }

  if (currentView === 'accessRequest') {
    return <AccessRequestPage onBackToLogin={() => setCurrentView('login')} />
  }

  if (currentView === 'legal') {
    return <LegalNoticesPage />
  }

  if (currentView === 'privacy') {
    return <PrivacyPage />
  }

  if (currentView === 'support') {
    return <SupportPage />
  }

  if (isRestoringSession) {
    return <main className="session-loading" role="status">Vérification de la session...</main>
  }

  if (currentView === 'adminDashboard' && isAuthenticated && currentUser) {
    return <AdminDashboardPage currentUser={currentUser} onLogout={handleLogout} onUserChange={setCurrentUser} />
  }

  return (
    <LoginPage
      initialError={sessionError}
      onOpenAccessRequest={() => setCurrentView('accessRequest')}
      onAuthenticated={(user) => {
        setCurrentUser(user)
        setCurrentView('adminDashboard')
      }}
    />
  )
}

function LoginPage({
  initialError,
  onOpenAccessRequest,
  onAuthenticated,
}: {
  initialError: string
  onOpenAccessRequest: () => void
  onAuthenticated: (user: User) => void
}) {
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState(initialError)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const emailInput = form.elements.namedItem('email') as HTMLInputElement | null
    const passwordInput = form.elements.namedItem('password') as HTMLInputElement | null

    if (!emailInput || !passwordInput) {
      setErrorMessage('Une erreur est survenue lors de la validation du formulaire.')
      return
    }

    const email = emailInput.value.trim()
    const password = passwordInput.value

    if (!email || !password) {
      setErrorMessage('Veuillez saisir votre email et votre mot de passe.')
      return
    }

    setErrorMessage('')
    setIsSubmitting(true)

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(data?.detail || 'Identifiants invalides.')
      }

      const token = data.access_token

      if (!token) {
        throw new Error('Le backend n’a pas renvoyé de token.')
      }

      const meResponse = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!meResponse.ok) {
        throw new Error('Impossible de récupérer le profil utilisateur.')
      }

      const user = (await meResponse.json().catch(() => null)) as User | null
      if (!user) {
        throw new Error('Profil utilisateur introuvable.')
      }

      activeAccessToken = token
      sessionStorage.setItem('access_token', token)
      onAuthenticated(user)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Une erreur est survenue lors de la connexion.'
      setErrorMessage(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <section className="brand-panel">
        <div className="brand-visual">
          <div className="brand-card">
            <img className="brand-logo" src={logo} alt="Trident Oil Services Logo" />
          </div>
        </div>

        <div className="brand-overlay">
          <div className="brand-content">
            <h1>Gestion des Cotations</h1>
            <p>
              Plateforme professionnelle dédiée à la gestion des cotations. Créez,
              gérez et suivez vos offres commerciales en toute simplicité tout en
              garantissant la fiabilité et la rapidité de vos processus.
            </p>

            <div className="brand-meta">
              <div className="meta-item">
                <span className="meta-label">Secteur</span>
                <span className="meta-value">Oil &amp; Gas</span>
              </div>
              <div className="meta-divider" />
              <div className="meta-item">
                <span className="meta-label">Technologie</span>
                <span className="meta-value">Application métier</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <main className="login-panel">
        <div className="login-shell">
          <div className="mobile-logo-wrap">
            <img className="mobile-logo" src={logo} alt="Trident Oil Services" />
          </div>

          <div className="intro-block">
            <h2>Bienvenue</h2>
            <p>Connectez-vous à votre espace de gestion des cotations</p>
          </div>

          <div className="login-card">
            <form className="login-form" onSubmit={handleSubmit} noValidate>
              <div className="field-group">
                <label htmlFor="email">Email</label>
                <div className="input-wrap">
                  <div className="input-icon material-symbols-outlined">mail</div>
                  <input id="email" name="email" type="email" placeholder="exemple@gmail.com" required />
                </div>
              </div>

              <div className="field-group">
                <div className="password-row">
                  <label htmlFor="password">Mot de passe</label>
                </div>
                <div className="input-wrap password-wrap">
                  <div className="input-icon material-symbols-outlined">lock</div>
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    required
                  />
                  <button
                    className="password-toggle"
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label="Afficher ou masquer le mot de passe"
                  >
                    <span className="material-symbols-outlined" id="password-toggle-icon">
                      {showPassword ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              {errorMessage ? <p className="form-error">{errorMessage}</p> : null}

              <div className="actions-block">
                <button className="primary-btn" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                  ) : (
                    <>
                      <span>Se connecter</span>
                      <span className="material-symbols-outlined text-[20px]">login</span>
                    </>
                  )}
                </button>

                <div className="divider-row">
                  <div className="divider-line" />
                  <span>Nouveau ici ?</span>
                  <div className="divider-line" />
                </div>

                <button className="secondary-btn" type="button" onClick={onOpenAccessRequest}>
                  Demander un accès
                </button>
              </div>
            </form>
          </div>

          <footer className="login-footer">
            <div className="footer-links">
              <a href="/support-technique">Support technique</a>
              <a href="/mentions-legales">Mentions légales</a>
              <a href="/confidentialite">Confidentialité</a>
            </div>
            <p>ProQuote ERP</p>
          </footer>
        </div>
      </main>
    </div>
  )
}

function AccessRequestPage({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [form, setForm] = useState<AccessFormState>(defaultAccessForm)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setErrorMessage('')
    setSuccessMessage('')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nomComplet = form.nomComplet.trim()
    const email = form.email.trim()
    const motDePasse = form.motDePasse
    const profilSouhaite = form.profilSouhaite

    if (!nomComplet) {
      setErrorMessage('Le nom complet est obligatoire.')
      return
    }

    if (!email) {
      setErrorMessage('L’email est obligatoire.')
      return
    }

    if (!motDePasse.trim()) {
      setErrorMessage('Le mot de passe est obligatoire.')
      return
    }

    if (motDePasse.length < 12 || motDePasse.length > 128) {
      setErrorMessage('Le mot de passe doit contenir entre 12 et 128 caractères.')
      return
    }

    if (!profilSouhaite || !['COMMERCIAL', 'MANAGER'].includes(profilSouhaite)) {
      setErrorMessage('Veuillez choisir un profil valide : Commercial ou Manager.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage('')
    setSuccessMessage('')

    try {
      const response = await fetch(`${API_BASE_URL}/access-requests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nomComplet,
          email,
          motDePasse,
          profilSouhaite,
        }),
      })

      const responseBody = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(responseBody?.detail || 'Une erreur est survenue lors de l’envoi de la demande.')
      }

      setSuccessMessage('Demande envoyée avec succès !')
      setForm(defaultAccessForm)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Une erreur est survenue lors de l’envoi de la demande.'
      setErrorMessage(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="access-request-page">
      <div className="access-request-card">
        <header className="access-request-header">
          <div className="access-request-logo-wrap">
            <img src={logo} alt="Trident Oil Services Logo" className="access-request-logo" />
          </div>

          <div className="access-request-title-wrap">
            <h1>Demande d'accès</h1>
            <p>Remplissez ce formulaire pour demander un accès à la plateforme de gestion.</p>
          </div>
        </header>

        <form className="access-request-form" onSubmit={handleSubmit} noValidate>
          <div className="field-group">
            <label htmlFor="nomComplet">Nom complet</label>
            <div className="input-wrap">
              <span className="input-icon material-symbols-outlined">person</span>
              <input
                id="nomComplet"
                name="nomComplet"
                type="text"
                placeholder="Jean Dupont"
                value={form.nomComplet}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="field-group">
            <label htmlFor="email">Email</label>
            <div className="input-wrap">
              <span className="input-icon material-symbols-outlined">mail</span>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="nom.prenom@gmail.com"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="field-group">
            <label htmlFor="motDePasse">Mot de passe</label>
            <div className="input-wrap">
              <span className="input-icon material-symbols-outlined">lock</span>
              <input
                id="motDePasse"
                name="motDePasse"
                type="password"
                placeholder="••••••••"
                value={form.motDePasse}
                onChange={handleChange}
                minLength={12}
                maxLength={128}
                required
              />
            </div>
          </div>

          <div className="field-group">
            <label htmlFor="profilSouhaite">Profil souhaité</label>
            <div className="input-wrap select-wrap">
              <span className="input-icon material-symbols-outlined">badge</span>
              <select
                id="profilSouhaite"
                name="profilSouhaite"
                value={form.profilSouhaite}
                onChange={handleChange}
                required
              >
                <option value="" disabled hidden>
                  Profil souhaité
                </option>
                <option value="COMMERCIAL">Commercial</option>
                <option value="MANAGER">Manager</option>
              </select>
              <span className="select-arrow material-symbols-outlined">expand_more</span>
            </div>
          </div>

          {errorMessage ? <p className="form-error access-form-error">{errorMessage}</p> : null}
          {successMessage ? <p className="success-message">{successMessage}</p> : null}

          <button className="primary-btn access-submit-btn" type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <span className="material-symbols-outlined animate-spin">progress_activity</span>
            ) : (
              <>
                <span>Envoyer la demande</span>
                <span className="material-symbols-outlined text-[18px]">send</span>
              </>
            )}
          </button>
        </form>

        <div className="access-request-link-row">
          <button type="button" className="access-request-link" onClick={onBackToLogin}>
            Déjà un compte ? Retour à la connexion
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>

      <footer className="access-request-footer">
        <p>ProQuote ERP</p>
      </footer>
    </main>
  )
}

function AdminDashboardPage({
  currentUser,
  onLogout,
  onUserChange,
}: {
  currentUser: User
  onLogout: (message?: string) => void
  onUserChange: (user: User) => void
}) {
  const [activePage, setActivePage] = useState<AdminPage>(() => getInitialAdminPage(currentUser.role))
  const [summary, setSummary] = useState<DashboardSummary>(defaultSummary)
  const [users, setUsers] = useState<User[]>([])
  const [accessRequests, setAccessRequests] = useState<AccessRequestItem[]>([])
  const [quotations, setQuotations] = useState<QuotationItem[]>([])
  const [quotationChart, setQuotationChart] = useState<QuotationChartPoint[]>([])
  const [quotationFormOpen, setQuotationFormOpen] = useState(false)
  const [quotationFormMode, setQuotationFormMode] = useState<'create' | 'edit'>('create')
  const [editingQuotationId, setEditingQuotationId] = useState<string | null>(null)
  const [quotationForm, setQuotationForm] = useState<QuotationFormState>(defaultQuotationForm)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [dashboardDataLoaded, setDashboardDataLoaded] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusMessage, setStatusMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [statusQuotation, setStatusQuotation] = useState<QuotationItem | null>(null)
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [passwordStatus, setPasswordStatus] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false)
  const statusMessageTimerRef = useRef<number | null>(null)
  const [isFilterOpen, setIsFilterOpen] = useState(false)

  useEffect(() => {
    return () => {
      if (statusMessageTimerRef.current) {
        window.clearTimeout(statusMessageTimerRef.current)
      }
    }
  }, [])

  const [filterStatus, setFilterStatus] = useState('')
  const avatarInputRef = useRef<HTMLInputElement | null>(null)
  const isAdmin = currentUser.role === 'ADMIN'
  const isEmployee = currentUser.role === 'COLLABORATEUR'
  const isManager = currentUser.role === 'RESPONSABLE'
  const pageLabels = {
    ...adminPageLabels,
    dashboard: isManager ? "Vue d'ensemble Manager" : adminPageLabels.dashboard,
    settings: 'Paramètres',
    help: 'Aide',
  }
  const visiblePages = isAdmin
    ? (['dashboard', 'devis', 'users', 'roles', 'settings', 'help'] as const)
    : isEmployee
    ? (['devis', 'settings', 'help'] as const)
    : (['dashboard', 'devis', 'settings', 'help'] as const)

  const syncPagePath = (page: AdminPage) => {
    const routeMap: Record<AdminPage, string> = {
      dashboard: '/dashboard',
      devis: '/devis',
      users: '/users',
      roles: '/roles',
      reports: '/rapports',
      settings: '/parametres',
      help: '/aide',
    }

    const nextPath = routeMap[page] || '/dashboard'
    const currentPath = window.location.pathname
    if (currentPath !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }
  }

  const emptyStateLabel = loading ? 'Chargement...' : ''
  const searchPlaceholder = `Rechercher dans ${pageLabels[activePage].toLowerCase()}`

  const handlePasswordFieldChange = (field: keyof typeof passwordForm) => (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value
    setPasswordForm((current) => ({ ...current, [field]: value }))
  }

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPasswordStatus(null)

    if (!passwordForm.old_password.trim() || !passwordForm.new_password.trim() || !passwordForm.confirm_password.trim()) {
      setPasswordStatus({ type: 'error', message: 'Tous les champs du mot de passe sont requis.' })
      return
    }

    if (passwordForm.new_password.length < 12 || passwordForm.new_password.length > 128) {
      setPasswordStatus({ type: 'error', message: 'Le nouveau mot de passe doit contenir entre 12 et 128 caractères.' })
      return
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordStatus({ type: 'error', message: 'La confirmation du nouveau mot de passe ne correspond pas.' })
      return
    }

    setIsPasswordSubmitting(true)

    try {
      const token = activeAccessToken
      const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password,
          confirm_password: passwordForm.confirm_password,
        }),
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(data?.detail || 'Impossible de modifier le mot de passe.')
      }

      if (typeof data?.access_token !== 'string' || !data.access_token) {
        throw new Error('Le mot de passe a été changé, mais le serveur n’a pas renvoyé de nouveau jeton.')
      }
      activeAccessToken = data.access_token
      sessionStorage.setItem('access_token', data.access_token)
      setPasswordForm({ old_password: '', new_password: '', confirm_password: '' })
      setPasswordStatus({ type: 'success', message: data?.message || 'Mot de passe modifié avec succès.' })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Une erreur est survenue.'
      setPasswordStatus({ type: 'error', message })
    } finally {
      setIsPasswordSubmitting(false)
    }
  }

  useEffect(() => {
    const fetchDashboardData = async () => {
      const token = activeAccessToken
      if (!token) {
        onLogout()
        return
      }

      const headers = {
        Authorization: `Bearer ${token}`,
      }

      try {
        const requests: Array<Promise<Response>> = [
          fetch(`${API_BASE_URL}/dashboard/summary`, { headers }),
          fetch(`${API_BASE_URL}/quotations/?skip=0&limit=500`, { headers }),
          fetch(`${API_BASE_URL}/dashboard/charts?type=by_month`, { headers }),
        ]

        if (isAdmin) {
          requests.push(fetch(`${API_BASE_URL}/users/?skip=0&limit=500`, { headers }))
          requests.push(fetch(`${API_BASE_URL}/access-requests`, { headers }))
        }

        const responses = await Promise.all(requests)
        if (responses.some((response) => response.status === 401)) {
          onLogout('Votre session a expiré. Veuillez vous reconnecter.')
          return
        }

        const [summaryPayload, quotationPayload, chartPayload] = await Promise.all([
          readApiResponse<DashboardSummary>(responses[0], 'Échec du chargement des statistiques.'),
          readApiResponse<PaginatedQuotationResponse>(responses[1], 'Échec du chargement des devis.'),
          readApiResponse<QuotationChartPoint[]>(responses[2], 'Échec du chargement du graphique.'),
        ])
        let usersPayload: User[] | null = null
        let requestPayload: AccessRequestItem[] | null = null
        if (isAdmin) {
          [usersPayload, requestPayload] = await Promise.all([
            readApiResponse<User[]>(responses[3], 'Échec du chargement des utilisateurs.'),
            readApiResponse<AccessRequestItem[]>(responses[4], 'Échec du chargement des demandes d’accès.'),
          ])
        }

        setSummary(summaryPayload)
        setQuotations(quotationPayload.items)
        setQuotationChart(chartPayload)
        if (usersPayload) setUsers(usersPayload)
        if (requestPayload) setAccessRequests(requestPayload)
        setDashboardDataLoaded(true)
        setErrorMessage('')
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : 'Impossible de charger les données du tableau de bord.')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
    const interval = window.setInterval(fetchDashboardData, 15000)

    return () => window.clearInterval(interval)
  }, [isAdmin, onLogout])

  useEffect(() => {
    return () => {
      if (statusMessageTimerRef.current) {
        window.clearTimeout(statusMessageTimerRef.current)
      }
    }
  }, [])

  const query = searchQuery.trim()
  const filteredUsers = users.filter((user) =>
    matchesQuery(query, user.full_name, user.email, user.role, user.is_active ? 'actif' : 'inactif', formatDateTime(user.created_at)),
  )
  const filteredRequests = accessRequests.filter((request) =>
    matchesQuery(query, request.nomComplet, request.email, request.profilSouhaite, request.status, formatDateTime(request.created_at)),
  )
  const filteredQuotations = quotations.filter((quotation) =>
    matchesQuery(query, quotation.reference, quotation.client_name, quotation.status, formatDateTime(quotation.creation_date)),
  ).filter((quotation) => {
    if (filterStatus && quotation.status !== filterStatus) {
      return false
    }
    return true
  })
  const filteredChart = quotationChart.filter((point) => matchesQuery(query, point.label, point.value))
  const openPage = (page: AdminPage) => {
    setActivePage(page)
    syncPagePath(page)
    setSearchQuery('')
    setStatusMessage('')
    setErrorMessage('')
  }

  const buildQuotationUrl = () => {
    const url = new URL(`${API_BASE_URL}/quotations/`)
    url.searchParams.set('skip', '0')
    url.searchParams.set('limit', '500')
    if (filterStatus) {
      url.searchParams.set('status', filterStatus)
    }
    return url.toString()
  }

  const refreshData = async () => {
    const token = activeAccessToken
    if (!token) {
      onLogout()
      return
    }

    const headers = {
      Authorization: `Bearer ${token}`,
    }

    const requests: Array<Promise<Response>> = [
      fetch(`${API_BASE_URL}/dashboard/summary`, { headers }),
      fetch(buildQuotationUrl(), { headers }),
      fetch(`${API_BASE_URL}/dashboard/charts?type=by_month`, { headers }),
    ]

    if (isAdmin) {
      requests.push(fetch(`${API_BASE_URL}/users/?skip=0&limit=500`, { headers }))
      requests.push(fetch(`${API_BASE_URL}/access-requests`, { headers }))
    }

    try {
      const responses = await Promise.all(requests)
      if (responses.some((response) => response.status === 401)) {
        onLogout('Votre session a expiré. Veuillez vous reconnecter.')
        return
      }

      const [summaryPayload, quotationPayload, chartPayload] = await Promise.all([
        readApiResponse<DashboardSummary>(responses[0], 'Échec du chargement des statistiques.'),
        readApiResponse<PaginatedQuotationResponse>(responses[1], 'Échec du chargement des devis.'),
        readApiResponse<QuotationChartPoint[]>(responses[2], 'Échec du chargement du graphique.'),
      ])
      let usersPayload: User[] | null = null
      let requestPayload: AccessRequestItem[] | null = null
      if (isAdmin) {
        [usersPayload, requestPayload] = await Promise.all([
          readApiResponse<User[]>(responses[3], 'Échec du chargement des utilisateurs.'),
          readApiResponse<AccessRequestItem[]>(responses[4], 'Échec du chargement des demandes d’accès.'),
        ])
      }

      setSummary(summaryPayload)
      setQuotations(quotationPayload.items)
      setQuotationChart(chartPayload)
      if (usersPayload) setUsers(usersPayload)
      if (requestPayload) setAccessRequests(requestPayload)
      setDashboardDataLoaded(true)
      setErrorMessage('')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Impossible de mettre à jour les données.')
    }
  }

  const handleCreateUser = async () => {
    const email = window.prompt('Email du nouvel utilisateur')?.trim()
    if (!email) return

    const password = window.prompt('Mot de passe du nouvel utilisateur')
    if (!password || !password.trim()) return
    if (password.length < 12 || password.length > 128) {
      window.alert('Le mot de passe doit contenir entre 12 et 128 caractères.')
      return
    }

    const fullName = window.prompt('Nom complet', '')?.trim() || ''
    const role = (window.prompt('Rôle (COLLABORATEUR, RESPONSABLE, ADMIN)', 'COLLABORATEUR') || '').trim().toUpperCase()
    if (!['COLLABORATEUR', 'RESPONSABLE', 'ADMIN'].includes(role)) {
      window.alert('Rôle invalide.')
      return
    }

    const token = activeAccessToken
    if (!token) return

    try {
      const response = await fetch(`${API_BASE_URL}/users/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || null,
          role,
        }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        if (response.status === 403) {
          window.alert('Accès refusé. Connectez-vous avec un compte administrateur pour ajouter un utilisateur.')
          return
        }
        window.alert(payload?.detail || 'Impossible de créer l’utilisateur.')
        return
      }

      setStatusMessage('Utilisateur créé avec succès.')
      await refreshData()
    } catch {
      window.alert('Erreur réseau: impossible de joindre le serveur.')
    }
  }

  const handleEditUser = async (user: User) => {
    const nextName = window.prompt('Nom complet', user.full_name || '')
    if (nextName === null) return

    const nextRole = window.prompt('Rôle (COLLABORATEUR, RESPONSABLE, ADMIN)', user.role)
    if (nextRole === null) return

    const normalizedRole = nextRole.trim().toUpperCase()
    if (!['COLLABORATEUR', 'RESPONSABLE', 'ADMIN'].includes(normalizedRole)) {
      window.alert('Rôle invalide.')
      return
    }

    const token = activeAccessToken
    if (!token) return

    const response = await fetch(`${API_BASE_URL}/users/${user.id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        full_name: nextName.trim() || null,
        role: normalizedRole,
        is_active: user.is_active,
      }),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      window.alert(payload?.detail || 'Impossible de modifier l’utilisateur.')
      return
    }

    setStatusMessage('Utilisateur mis à jour.')
    await refreshData()
  }

  const handleDeleteUser = async (user: User) => {
    const confirmed = window.confirm(`Supprimer ${user.full_name || user.email} ?`)
    if (!confirmed) return

    const token = activeAccessToken
    if (!token) return

    const response = await fetch(`${API_BASE_URL}/users/${user.id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      window.alert(payload?.detail || 'Impossible de supprimer l’utilisateur.')
      return
    }

    setUsers((currentUsers) => currentUsers.filter((item) => item.id !== user.id))
    setAccessRequests((currentRequests) => currentRequests.filter((item) => item.email !== user.email))
    setStatusMessage('Utilisateur supprimé.')
    await refreshData()
  }

  const handleAcceptRequest = async (request: AccessRequestItem) => {
    const token = activeAccessToken
    if (!token) return

    const response = await fetch(`${API_BASE_URL}/access-requests/${request.id}/status`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status: 'ACCEPTEE' }),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      window.alert(payload?.detail || 'Impossible de valider la demande.')
      return
    }

    setAccessRequests((currentRequests) => currentRequests.filter((item) => item.id !== request.id))
    setStatusMessage('Demande acceptée.')
    await refreshData()
  }

  const handleDeleteAccessRequest = async (request: AccessRequestItem) => {
    if (!window.confirm(`Supprimer la demande de ${request.nomComplet} ?`)) return

    const token = activeAccessToken
    if (!token) return

    const response = await fetch(`${API_BASE_URL}/access-requests/${request.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      window.alert(payload?.detail || 'Impossible de supprimer la demande.')
      return
    }

    setAccessRequests((currentRequests) => currentRequests.filter((item) => item.id !== request.id))
    setStatusMessage('Demande supprimée.')
    await refreshData()
  }

  const getStatusBadge = (status?: string) => {
    const normalized = String(status || '').trim().toUpperCase()
    if (normalized === 'BROUILLON') {
      return { label: 'En attente', className: 'status-badge pending' }
    }
    if (normalized === 'ENVOYEE') {
      return { label: 'Envoyé', className: 'status-badge sent' }
    }
    if (normalized === 'ACCEPTEE') {
      return { label: 'Validé', className: 'status-badge accepted' }
    }
    if (normalized === 'REFUSEE') {
      return { label: 'Refusé', className: 'status-badge refused' }
    }
    if (normalized === 'EXPIREE') {
      return { label: 'Expiré', className: 'status-badge expired' }
    }
    return { label: 'Inconnu', className: 'status-badge unknown' }
  }

  const getAvailableQuotationStatuses = (status: string) => {
    const normalized = String(status || '').trim().toUpperCase()
    if (normalized === 'ENVOYEE') return ['ACCEPTEE', 'REFUSEE']
    if (normalized === 'BROUILLON') return ['ENVOYEE']
    return []
  }

  const canManageQuotationStatus = currentUser?.role === 'ADMIN' || currentUser?.role === 'RESPONSABLE'

  const resetQuotationForm = () => {
    setQuotationForm({ ...defaultQuotationForm })
    setEditingQuotationId(null)
    setQuotationFormMode('create')
  }

  const handleOpenCreateQuotation = () => {
    resetQuotationForm()
    setQuotationFormOpen(true)
  }

  const handleOpenEditQuotation = async (quotation: QuotationItem) => {
    const token = activeAccessToken
    if (!token) return

    const response = await fetch(`${API_BASE_URL}/quotations/${quotation.id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      window.alert(payload?.detail || 'Impossible de charger le devis.')
      return
    }

    const quotationDetails = (await response.json().catch(() => null)) as {
      client_name?: string
      client_email?: string
      client_address?: string | null
      client_reference?: string | null
      validity_date?: string
      delivery_duration?: string | null
      incoterm?: string | null
      special_conditions?: string | null
      vat_mode?: string
      vat_code?: string | null
      vat_rate?: number | string | null
      payment_method?: string | null
      payment_terms?: string | null
      articles?: Array<{ designation: string; quantity: number; unit?: string | null; unit_price: number }>
    } | null

    if (!quotationDetails) return

    setQuotationForm({
      client_name: quotationDetails.client_name || quotation.client_name,
      client_email: quotationDetails.client_email || '',
      client_address: quotationDetails.client_address || '',
      client_reference: quotationDetails.client_reference || '',
      validity_date: quotationDetails.validity_date || new Date().toISOString().slice(0, 10),
      delivery_duration: quotationDetails.delivery_duration || '',
      incoterm: quotationDetails.incoterm || '',
      special_conditions: quotationDetails.special_conditions || '',
      vat_mode: quotationDetails.vat_mode || 'sans_tva',
      vat_code: quotationDetails.vat_code || '',
      vat_rate: quotationDetails.vat_rate == null ? '' : String(quotationDetails.vat_rate),
      payment_method: quotationDetails.payment_method || '',
      payment_terms: quotationDetails.payment_terms || '',
      articles:
        quotationDetails.articles?.map((article) => ({
          designation: article.designation,
          quantity: Number(article.quantity) || 1,
          unit: article.unit || '',
          unit_price: Number(article.unit_price) || 0,
          line_total: Number(article.quantity || 0) * Number(article.unit_price || 0),
        })) || [{ ...defaultArticleLine }],
    })
    setEditingQuotationId(quotation.id)
    setQuotationFormMode('edit')
    setQuotationFormOpen(true)
  }

  const calculateArticleLineTotal = (article: ArticleLine) =>
    Math.round((article.quantity * article.unit_price + Number.EPSILON) * 100) / 100

  const handleQuotationFormChange = (field: keyof QuotationFormState, value: string) => {
    setQuotationForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  const handleIncotermSelectChange = (value: string) => {
    if (value === 'AUTRE') {
      setQuotationForm((current) => ({
        ...current,
        incoterm: getCustomIncotermValue(current.incoterm),
      }))
      return
    }

    setQuotationForm((current) => ({
      ...current,
      incoterm: value,
    }))
  }

  const handleArticleChange = (index: number, field: keyof ArticleLine, value: string) => {
    setQuotationForm((current) => {
      const nextArticles = [...current.articles]
      const article = { ...nextArticles[index], [field]: field === 'designation' || field === 'unit' ? value : Number(value) }
      article.line_total = calculateArticleLineTotal(article)
      nextArticles[index] = article
      return { ...current, articles: nextArticles }
    })
  }

  const handleAddArticle = () => {
    setQuotationForm((current) => ({
      ...current,
      articles: [...current.articles, { ...defaultArticleLine }],
    }))
  }

  const handleRemoveArticle = (index: number) => {
    setQuotationForm((current) => ({
      ...current,
      articles: current.articles.filter((_, position) => position !== index),
    }))
  }

  const handleSubmitQuotation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const token = activeAccessToken
    if (!token) return

    const payload = {
      client_name: quotationForm.client_name.trim(),
      client_email: quotationForm.client_email.trim(),
      client_address: quotationForm.client_address.trim() || null,
      client_reference: quotationForm.client_reference.trim() || null,
      validity_date: quotationForm.validity_date,
      delivery_duration: quotationForm.delivery_duration.trim(),
      incoterm: quotationForm.incoterm.trim(),
      special_conditions: quotationForm.special_conditions.trim() || null,
      vat_mode: quotationForm.vat_mode,
      vat_code: quotationForm.vat_mode === 'avec_tva' ? quotationForm.vat_code.trim() : null,
      vat_rate: quotationForm.vat_mode === 'avec_tva' ? Number(quotationForm.vat_rate) : null,
      payment_method: quotationForm.payment_method.trim() || null,
      payment_terms: quotationForm.payment_terms.trim() || null,
      articles: quotationForm.articles.map((article) => ({
        designation: article.designation.trim(),
        quantity: article.quantity,
        unit: article.unit.trim() || null,
        unit_price: article.unit_price,
      })),
    }

    if (!payload.client_name || !payload.client_email || !payload.validity_date || !payload.delivery_duration || !payload.incoterm) {
      window.alert('Veuillez remplir tous les champs obligatoires du devis.')
      return
    }

    if (
      !payload.vat_mode ||
      (payload.vat_mode === 'avec_tva' &&
        (!payload.vat_code ||
          payload.vat_rate == null ||
          !Number.isFinite(payload.vat_rate) ||
          payload.vat_rate <= 0 ||
          payload.vat_rate > 100))
    ) {
      window.alert('Choisissez le régime de TVA. Si la TVA s’applique, renseignez son code et son taux.')
      return
    }

    if (
      !payload.articles.length ||
      payload.articles.some(
        (article) =>
          !article.designation ||
          !Number.isFinite(article.quantity) ||
          article.quantity <= 0 ||
          !Number.isFinite(article.unit_price) ||
          article.unit_price < 0,
      )
    ) {
      window.alert('Chaque article doit avoir une désignation, une quantité positive et un prix unitaire valide.')
      return
    }

    const method = quotationFormMode === 'edit' && editingQuotationId ? 'PUT' : 'POST'
    const url = quotationFormMode === 'edit' && editingQuotationId ? `${API_BASE_URL}/quotations/${editingQuotationId}` : `${API_BASE_URL}/quotations/`

    const response = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const payloadError = await response.json().catch(() => ({}))
      window.alert(payloadError?.detail || 'Impossible d’enregistrer le devis.')
      return
    }

    const isCreateMode = quotationFormMode !== 'edit' || !editingQuotationId
    if (isCreateMode) {
      if (statusMessageTimerRef.current) {
        window.clearTimeout(statusMessageTimerRef.current)
      }
      setStatusMessage('Devis créé avec succès.')
      statusMessageTimerRef.current = window.setTimeout(() => {
        setStatusMessage('')
        statusMessageTimerRef.current = null
      }, 5000)
    } else {
      setStatusMessage('Devis mis à jour avec succès.')
    }

    setQuotationFormOpen(false)
    resetQuotationForm()
    await refreshData()
  }

  const handleDownloadPdf = async (quotation: QuotationItem) => {
    const token = activeAccessToken
    if (!token) return

    setActionLoadingId(quotation.id)
    try {
      const pdfResponse = await fetch(`${API_BASE_URL}/quotations/${quotation.id}/generate-pdf`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!pdfResponse.ok) {
        const payload = await pdfResponse.json().catch(() => ({}))
        window.alert(payload?.detail || 'Impossible de générer le PDF.')
        return
      }

      const fileResponse = await fetch(`${API_BASE_URL}/quotations/${quotation.id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!fileResponse.ok) {
        const payload = await fileResponse.json().catch(() => ({}))
        window.alert(payload?.detail || 'Impossible de télécharger le PDF.')
        return
      }

      const blob = await fileResponse.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${quotation.reference}.pdf`
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleSendQuotation = async (quotation: QuotationItem) => {
    const token = activeAccessToken
    if (!token) return

    setActionLoadingId(quotation.id)
    try {
      const response = await fetch(`${API_BASE_URL}/quotations/${quotation.id}/send`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        window.alert(payload?.detail || 'Impossible d’envoyer le devis par email.')
        return
      }

      if (statusMessageTimerRef.current) {
        window.clearTimeout(statusMessageTimerRef.current)
      }
      setStatusMessage('Quotation envoyé par email avec succès.')
      statusMessageTimerRef.current = window.setTimeout(() => {
        setStatusMessage('')
        statusMessageTimerRef.current = null
      }, 5000)

      await refreshData()
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleChangeQuotationStatus = async (newStatus: string) => {
    if (!statusQuotation) return

    const token = activeAccessToken
    if (!token) return

    setActionLoadingId(statusQuotation.id)
    try {
      const response = await fetch(`${API_BASE_URL}/quotations/${statusQuotation.id}/status`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ new_status: newStatus }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        window.alert(payload?.detail || 'Impossible de modifier le statut du devis.')
        return
      }

      setStatusQuotation(null)
      setStatusMessage('Statut du devis mis à jour.')
      await refreshData()
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleRoleChange = async (user: User, nextRole: string) => {
    if (!['COLLABORATEUR', 'RESPONSABLE', 'ADMIN'].includes(nextRole)) {
      window.alert('Rôle invalide.')
      return
    }

    const token = activeAccessToken
    if (!token) return

    const response = await fetch(`${API_BASE_URL}/users/${user.id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        full_name: user.full_name || null,
        role: nextRole,
        is_active: user.is_active,
      }),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      window.alert(payload?.detail || 'Impossible de mettre à jour le rôle.')
      return
    }

    setUsers((currentUsers) =>
      currentUsers.map((currentUserItem) =>
        currentUserItem.id === user.id ? { ...currentUserItem, role: nextRole } : currentUserItem,
      ),
    )

    if (user.id === currentUser?.id) {
      onUserChange({ ...currentUser, role: nextRole })
    }

    setStatusMessage('Rôle mis à jour.')
    await refreshData()
  }

  const handleAvatarPicker = () => {
    avatarInputRef.current?.click()
  }

  const handleAvatarChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    const reader = new FileReader()
    reader.onload = async () => {
      const avatarUrl = typeof reader.result === 'string' ? reader.result : ''
      if (!avatarUrl) return

      const token = activeAccessToken
      if (!token) return

      const response = await fetch(`${API_BASE_URL}/users/me/avatar`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ avatar_url: avatarUrl }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        window.alert(payload?.detail || 'Impossible de modifier la photo de profil.')
        return
      }

      const updatedUser = (await response.json().catch(() => null)) as User | null
      if (updatedUser) {
        onUserChange(updatedUser)
      }
      setStatusMessage('Photo de profil mise à jour.')
      await refreshData()
    }

    reader.readAsDataURL(file)
  }

  const renderSearchResultsCount = () => {
    if (activePage === 'users') {
      return `${filteredUsers.length} utilisateur(s) et ${filteredRequests.length} demande(s)`
    }

    if (activePage === 'roles') {
      return `${filteredUsers.length} utilisateur(s)`
    }

    if (activePage === 'devis') {
      return `${filteredQuotations.length} devis`
    }

    if (activePage === 'dashboard') {
      return `${filteredChart.length} point(s) de graphique`
    }

    return emptyStateLabel
  }

  const renderCurrentPage = () => {
    if (currentUser.role === 'RESPONSABLE' && activePage === 'dashboard') {
      const managerSeries = buildMonthlyChartSeries(filteredChart)

      return (
        <>
          <section className="manager-welcome">
            <div>
              <h2>Bonjour, {currentUser.full_name || ''}</h2>
              <p>Voici l'état actuel de vos cotations et services Trident Oil.</p>
            </div>
            <div className="manager-welcome-actions">
              <button type="button" className="manager-secondary-action" onClick={() => window.print()}>
                <span className="material-symbols-outlined">download</span>
                Exporter Rapport
              </button>
            </div>
          </section>

          <section className="manager-stats-grid">
            <div className="manager-stat-card"><span className="material-symbols-outlined manager-stat-icon blue">description</span><p>Total Devis</p><strong>{summary.total_quotations || 0}</strong></div>
            <div className="manager-stat-card"><span className="material-symbols-outlined manager-stat-icon orange">pending_actions</span><p>En attente</p><strong>{summary.draft_count || 0}</strong></div>
            <div className="manager-stat-card"><span className="material-symbols-outlined manager-stat-icon green">check_circle</span><p>Validés</p><strong>{summary.accepted_count || 0}</strong></div>
            <div className="manager-stat-card"><span className="material-symbols-outlined manager-stat-icon red">trending_up</span><p>Taux de Conversion</p><strong>{formatPercent(summary.conversion_rate)}</strong></div>
          </section>

          <section className="manager-lower-grid">
            <div className="manager-chart-panel">
              <h3>Performance mensuelle</h3>
              <p>Création réelle des cotations par mois.</p>
              <div className="horizontal-monthly-chart" aria-label="Graphique mensuel dynamique des cotations">
                {managerSeries.series.map(({ label, value }) => {
                  const width = managerSeries.normalizedMax > 0 ? `${Math.max((value / managerSeries.normalizedMax) * 100, value > 0 ? 10 : 0)}%` : '0%'
                  return (
                    <div key={label} className="monthly-bar-row">
                      <span className="monthly-bar-month">{label}</span>
                      <div className="monthly-bar-track">
                        <div className="monthly-bar-fill" style={{ width }} />
                      </div>
                      <span className="monthly-bar-value">{value}</span>
                    </div>
                  )
                })}
              </div>
              <div className="chart-year-label">{managerSeries.year}</div>
            </div>
          </section>

          {statusQuotation ? <div className="manager-modal-backdrop" role="presentation" onClick={() => setStatusQuotation(null)}><div className="manager-status-modal" role="dialog" aria-modal="true" aria-labelledby="manager-status-title" onClick={(event) => event.stopPropagation()}><div className="manager-modal-heading"><h3 id="manager-status-title">Modifier Statut</h3><button type="button" onClick={() => setStatusQuotation(null)} aria-label="Fermer"><span className="material-symbols-outlined">close</span></button></div>{getAvailableQuotationStatuses(statusQuotation.status).length ? getAvailableQuotationStatuses(statusQuotation.status).map((status) => <button type="button" className="manager-status-option" key={status} onClick={() => handleChangeQuotationStatus(status)}>{getStatusBadge(status).label}</button>) : <p className="manager-status-empty">Aucune transition autorisée depuis « {getStatusBadge(statusQuotation.status).label} ».</p>}<button type="button" className="manager-cancel-action" onClick={() => setStatusQuotation(null)}>Annuler</button></div></div> : null}
        </>
      )
    }

    if (activePage === 'dashboard') {
      const dashboardSeries = buildMonthlyChartSeries(filteredChart)
      const pendingRequests = accessRequests.filter((request) => request.status === 'EN_ATTENTE').length

      return (
        <>
          <section className="stats-grid">
            <div className="stat-card">
              <div>
                <p>Devis effectués</p>
                <h3>{summary.total_quotations || 0}</h3>
                <div className="stat-trend up">
                  <span className="material-symbols-outlined">trending_up</span>
                  {summary.total_quotations > 0 ? <span>Données réelles du système</span> : null}
                </div>
              </div>
              <div className="stat-icon primary">
                <span className="material-symbols-outlined">description</span>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <p>Montant total des devis</p>
                <h3>{formatCurrency(summary.total_amount)}</h3>
                <div className="stat-trend up">
                  <span className="material-symbols-outlined">payments</span>
                  {summary.total_amount > 0 ? <span>Valeur réelle du backend</span> : null}
                </div>
              </div>
              <div className="stat-icon secondary">
                <span className="material-symbols-outlined">payments</span>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <p>Devis en attente</p>
                <h3>{summary.draft_count || 0}</h3>
                <div className="stat-trend tertiary">
                  <span className="material-symbols-outlined">schedule</span>
                  {summary.draft_count > 0 ? <span>{`${summary.draft_count} dossiers`}</span> : null}
                </div>
              </div>
              <div className="stat-icon tertiary">
                <span className="material-symbols-outlined">pending_actions</span>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <p>Taux de conversion</p>
                <h3>{formatPercent(summary.conversion_rate)}</h3>
                <div className="stat-trend up">
                  <span className="material-symbols-outlined">auto_graph</span>
                  {summary.conversion_rate > 0 ? <span>Performance réelle</span> : null}
                </div>
              </div>
              <div className="stat-icon primary soft">
                <span className="material-symbols-outlined">leaderboard</span>
              </div>
            </div>
          </section>

          <div className="dashboard-grid">
            <aside className="alert-panel alert-panel-wide">
              <h3>Alerte système</h3>
              <div className="alert-card">
                <div className="alert-header">
                  <span>Nouvelle demande d'accès</span>
                  <span className="live-badge">DIRECT</span>
                </div>

                <div className="alert-list alert-count">
                  <div className="alert-count-number">{pendingRequests || 0}</div>
                  <div className="alert-count-label">Nouvelle demande d'accès : {pendingRequests || 0}</div>
                </div>
              </div>
            </aside>

            <section className="chart-panel chart-panel-wide">
              <div className="panel-header">
                <div>
                  <h3>Nombre de devis effectués</h3>
                  <p>Graphique alimenté uniquement par les données réelles du système.</p>
                </div>
              </div>

              <div className="horizontal-monthly-chart" aria-label="Graphique horizontal mensuel du nombre de devis effectués">
                {dashboardSeries.series.map(({ label, value }) => {
                  const width = dashboardSeries.normalizedMax > 0 ? `${Math.max((value / dashboardSeries.normalizedMax) * 100, value > 0 ? 10 : 0)}%` : '0%'
                  return (
                    <div key={label} className="monthly-bar-row">
                      <span className="monthly-bar-month">{label}</span>
                      <div className="monthly-bar-track">
                        <div className="monthly-bar-fill" style={{ width }} />
                      </div>
                      <span className="monthly-bar-value">{value}</span>
                    </div>
                  )
                })}
              </div>
              <div className="chart-year-label">{dashboardSeries.year}</div>
            </section>
          </div>
        </>
      )
    }

    if (activePage === 'users') {
      return (
        <div className="management-grid">
          <section className="table-panel">
            <div className="panel-header">
              <div>
                <h3>Utilisateurs</h3>
                <p>Gestion complète des comptes et demandes d’accès.</p>
              </div>
              <button type="button" className="add-user-button" onClick={handleCreateUser}>
                <span className="material-symbols-outlined">person_add</span>
                Ajouter un utilisateur
              </button>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Nom</th>
                    <th>Email</th>
                    <th>Rôle</th>
                    <th>Création</th>
                    <th>Statut</th>
                    <th className="actions-col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.length > 0 ? (
                    filteredUsers.map((user) => {
                      const initials = (user.full_name || user.email)
                        .split(' ')
                        .map((part) => part[0])
                        .join('')
                        .slice(0, 2)
                        .toUpperCase()

                      return (
                        <tr key={user.id}>
                          <td>
                            <div className="user-name-cell">
                              <div className="user-avatar">{initials || 'NA'}</div>
                              <div>
                                <div>{user.full_name || user.email}</div>
                                <div className="user-subtitle">{user.email}</div>
                              </div>
                            </div>
                          </td>
                          <td>{user.email}</td>
                          <td>
                            <span className={`role-pill ${getRoleClassName(user.role)}`}>
                              {user.role}
                            </span>
                          </td>
                          <td>{formatDateTime(user.created_at)}</td>
                          <td>
                            <span className={`status-row ${user.is_active ? 'active' : 'inactive'}`}>
                              <span className="status-dot" />
                              {user.is_active ? 'Actif' : 'Inactif'}
                            </span>
                          </td>
                          <td className="actions-col">
                            <div className="action-buttons">
                              <button type="button" aria-label="Modifier" onClick={() => handleEditUser(user)}>
                                <span className="material-symbols-outlined">edit</span>
                              </button>
                              <button type="button" aria-label="Supprimer" className="danger" onClick={() => handleDeleteUser(user)}>
                                <span className="material-symbols-outlined">delete</span>
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td colSpan={6} className="empty-cell">{emptyStateLabel}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="table-panel">
            <div className="panel-header">
              <div>
                <h3>Demandes d'accès</h3>
                <p>Toutes les demandes sont gérées ici uniquement.</p>
              </div>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Demandeur</th>
                    <th>Email</th>
                    <th>Profil</th>
                    <th>Création</th>
                    <th>Statut</th>
                    <th className="actions-col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRequests.length > 0 ? (
                    filteredRequests.map((request) => (
                      <tr key={request.id}>
                        <td>{request.nomComplet}</td>
                        <td>{request.email}</td>
                        <td>{request.profilSouhaite === 'COMMERCIAL' ? 'Commercial' : 'Manager'}</td>
                        <td>{formatDateTime(request.created_at)}</td>
                        <td>
                          <span className={`request-status ${getRequestStatusPresentation(request.status).className}`}>
                            {getRequestStatusPresentation(request.status).label}
                          </span>
                        </td>
                        <td className="actions-col">
                          <div className="action-buttons">
                            {request.status === 'EN_ATTENTE' ? (
                              <>
                                <button type="button" aria-label="Accepter" onClick={() => handleAcceptRequest(request)}>
                                  <span className="material-symbols-outlined">check</span>
                                </button>
                                <button type="button" aria-label="Supprimer" className="danger" onClick={() => handleDeleteAccessRequest(request)}>
                                  <span className="material-symbols-outlined">delete</span>
                                </button>
                              </>
                            ) : (
                              <span className="request-readonly">Confirmée</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="empty-cell">{emptyStateLabel}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )
    }

    if (activePage === 'devis') {
      return (
        <section className="employee-dashboard-shell">
          <div className="employee-dashboard-header">
            <div>
              <h3 className="employee-dashboard-title">{isEmployee ? 'Historique de vos devis' : 'Historique des devis du système'}</h3>
              <p className="employee-dashboard-description">{isEmployee ? 'Gérez vos cotations récentes et envoyez-les au client.' : 'Gérez les cotations et envoyez-les au client.'}</p>
            </div>
            <button type="button" className="employee-new-quotation-btn" onClick={handleOpenCreateQuotation}>
              <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>add_circle</span>
              Nouveau Devis
            </button>
          </div>

          <div className="employee-stats-grid">
            <div className="employee-stat-card">
              <div className="employee-stat-icon stat-icon primary">
                <span className="material-symbols-outlined">description</span>
              </div>
              <div>
                <p>{isEmployee ? 'Mes devis' : 'Total devis'}</p>
                <strong>{summary.total_quotations || 0}</strong>
              </div>
            </div>
            <div className="employee-stat-card">
              <div className="employee-stat-icon stat-icon tertiary">
                <span className="material-symbols-outlined">pending_actions</span>
              </div>
              <div>
                <p>En attente</p>
                <strong>{summary.draft_count || 0}</strong>
              </div>
            </div>
            <div className="employee-stat-card">
              <div className="employee-stat-icon manager-stat-icon green">
                <span className="material-symbols-outlined">check_circle</span>
              </div>
              <div>
                <p>Validés</p>
                <strong>{summary.accepted_count || 0}</strong>
              </div>
            </div>
            <div className="employee-stat-card">
              <div className="employee-stat-icon collaborator-cancelled-icon">
                <span className="material-symbols-outlined">cancel</span>
              </div>
              <div>
                <p>Annulés</p>
                <strong>{summary.refused_count || 0}</strong>
              </div>
            </div>
          </div>

          <div className="employee-table-card">
            <div className="employee-table-toolbar">
              <div>
                <h4>{isEmployee ? 'Historique de vos devis' : 'Historique des devis du système'}</h4>
                <p>{isEmployee ? 'Voici vos cotations personnelles, générées uniquement depuis le backend.' : 'Voici les cotations du système, générées depuis le backend.'}</p>
              </div>
              <button type="button" className="employee-filter-btn" onClick={() => setIsFilterOpen((current) => !current)}>
                <span className="material-symbols-outlined">filter_list</span>
                Filtrer
              </button>
            </div>

            {isFilterOpen ? (
              <div className="employee-filter-panel">
                <div className="employee-filter-row">
                  <label>Statut</label>
                  <select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)}>
                    <option value="">Tous les statuts</option>
                    <option value="BROUILLON">En attente</option>
                    <option value="ENVOYEE">Envoyé</option>
                    <option value="ACCEPTEE">Validé</option>
                    <option value="REFUSEE">Annulé</option>
                    <option value="EXPIREE">Expiré</option>
                  </select>
                </div>
              </div>
            ) : null}

            <div className="employee-table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Référence</th>
                    <th>Client</th>
                    <th>Date</th>
                    <th>Montant</th>
                    <th className="text-center">Statut</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredQuotations.length > 0 ? (
                    filteredQuotations.map((quotation) => {
                      const statusBadge = getStatusBadge(quotation.status)
                      return (
                        <tr key={quotation.id} className="employee-table-row">
                          <td>
                            <span className="employee-quote-reference">{quotation.reference}</span>
                          </td>
                          <td>
                            <div className="employee-client-cell">
                              <span className="employee-client-name">{quotation.client_name}</span>
                            </div>
                          </td>
                          <td>{formatDateTime(quotation.creation_date)}</td>
                          <td>{formatCurrency(quotation.total_amount)}</td>
                          <td className="text-center">
                            <span className={statusBadge.className}>{statusBadge.label}</span>
                          </td>
                          <td className="text-right">
                            <div className="employee-action-buttons">
                              <button
                                type="button"
                                disabled={actionLoadingId === quotation.id}
                                title="Modifier"
                                onClick={() => handleOpenEditQuotation(quotation)}
                                className="employee-action-btn"
                              >
                                <span className="material-symbols-outlined">edit</span>
                              </button>
                              {canManageQuotationStatus ? (
                                <button
                                  type="button"
                                  disabled={actionLoadingId === quotation.id}
                                  title="Modifier le statut"
                                  onClick={() => setStatusQuotation(quotation)}
                                  className="employee-action-btn"
                                >
                                  <span className="material-symbols-outlined">swap_horiz</span>
                                </button>
                              ) : null}
                              <button
                                type="button"
                                disabled={actionLoadingId === quotation.id}
                                title="Télécharger PDF"
                                onClick={() => handleDownloadPdf(quotation)}
                                className="employee-action-btn"
                              >
                                <span className="material-symbols-outlined">picture_as_pdf</span>
                              </button>
                              <button
                                type="button"
                                disabled={actionLoadingId === quotation.id}
                                title="Envoyer par email"
                                onClick={() => handleSendQuotation(quotation)}
                                className="employee-action-btn"
                              >
                                <span className="material-symbols-outlined">send</span>
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td colSpan={6} className="employee-empty-state">{emptyStateLabel}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {statusQuotation ? (
            <div className="manager-modal-backdrop" role="presentation" onClick={() => setStatusQuotation(null)}>
              <div className="manager-status-modal" role="dialog" aria-modal="true" aria-labelledby="status-quotation-title" onClick={(event) => event.stopPropagation()}>
                <div className="manager-modal-heading">
                  <h3 id="status-quotation-title">Modifier Statut</h3>
                  <button type="button" onClick={() => setStatusQuotation(null)} aria-label="Fermer">
                    <span className="material-symbols-outlined">close</span>
                  </button>
                </div>

                {getAvailableQuotationStatuses(statusQuotation.status).length ? (
                  getAvailableQuotationStatuses(statusQuotation.status).map((status) => (
                    <button type="button" className="manager-status-option" key={status} onClick={() => handleChangeQuotationStatus(status)}>
                      {getStatusBadge(status).label}
                    </button>
                  ))
                ) : (
                  <p className="manager-status-empty">Aucune transition autorisée depuis « {getStatusBadge(statusQuotation.status).label} ».</p>
                )}

                <button type="button" className="manager-cancel-action" onClick={() => setStatusQuotation(null)}>
                  Annuler
                </button>
              </div>
            </div>
          ) : null}

          {quotationFormOpen ? (
            <div className="employee-drawer-backdrop">
              <div className="employee-drawer">
                <div className="employee-drawer-header">
                  <div>
                    <h3>{quotationFormMode === 'edit' ? 'Modifier le devis' : 'Nouveau devis'}</h3>
                    <p>Créez et modifiez votre quotation avant envoi.</p>
                  </div>
                  <button type="button" onClick={() => setQuotationFormOpen(false)} className="icon-button">
                    <span className="material-symbols-outlined">close</span>
                  </button>
                </div>
                <form className="employee-drawer-form" onSubmit={handleSubmitQuotation}>
                  <div className="form-section">
                    <div className="form-row">
                      <label>Client</label>
                      <input
                        type="text"
                        value={quotationForm.client_name}
                        onChange={(event) => handleQuotationFormChange('client_name', event.target.value)}
                        placeholder="Nom du client"
                        required
                      />
                    </div>
                    <div className="form-row">
                      <label>Email client</label>
                      <input
                        type="email"
                        value={quotationForm.client_email}
                        onChange={(event) => handleQuotationFormChange('client_email', event.target.value)}
                        placeholder="client@example.com"
                        required
                      />
                    </div>
                    <div className="form-row">
                      <label>Adresse</label>
                      <input
                        type="text"
                        value={quotationForm.client_address}
                        onChange={(event) => handleQuotationFormChange('client_address', event.target.value)}
                        placeholder="Adresse du client"
                      />
                    </div>
                    <div className="form-row">
                      <label>Référence client</label>
                      <input
                        type="text"
                        value={quotationForm.client_reference}
                        onChange={(event) => handleQuotationFormChange('client_reference', event.target.value)}
                        placeholder="Référence client"
                      />
                    </div>
                    <div className="form-row">
                      <label>Date de validité</label>
                      <input
                        type="date"
                        value={quotationForm.validity_date}
                        onChange={(event) => handleQuotationFormChange('validity_date', event.target.value)}
                        required
                      />
                    </div>
                    <div className="form-row">
                      <label>Délai de livraison</label>
                      <input
                        type="text"
                        value={quotationForm.delivery_duration}
                        onChange={(event) => handleQuotationFormChange('delivery_duration', event.target.value)}
                        placeholder="Ex: 30 jours"
                        required
                      />
                    </div>
                    <div className="form-row">
                      <label>INCOTERM</label>
                      <select
                        value={getIncotermSelectValue(quotationForm.incoterm)}
                        onChange={(event) => handleIncotermSelectChange(event.target.value)}
                        required
                      >
                        <option value="DDP">DDP</option>
                        <option value="EXW">EXW / EXwork</option>
                        <option value="CPT">CPT</option>
                        <option value="CFR">CFR</option>
                        <option value="AUTRE">Autre</option>
                      </select>
                    </div>

                    {getIncotermSelectValue(quotationForm.incoterm) === 'AUTRE' ? (
                      <div className="form-row">
                        <label>Incoterm personnalisé</label>
                        <input
                          type="text"
                          value={getCustomIncotermValue(quotationForm.incoterm)}
                          onChange={(event) => handleQuotationFormChange('incoterm', event.target.value)}
                          placeholder="Saisir l'incoterm personnalisé"
                          required
                        />
                      </div>
                    ) : null}

                    <div className="form-row full-width">
                      <label>Conditions spéciales</label>
                      <textarea
                        value={quotationForm.special_conditions}
                        onChange={(event) => handleQuotationFormChange('special_conditions', event.target.value)}
                        placeholder="Notes complémentaires"
                      />
                    </div>
                    <div className="form-row">
                      <label>Régime de TVA</label>
                      <select
                        value={quotationForm.vat_mode}
                        onChange={(event) => handleQuotationFormChange('vat_mode', event.target.value)}
                        required
                      >
                        <option value="">Choisir un régime</option>
                        <option value="sans_tva">Sans TVA</option>
                        <option value="avec_tva">TVA applicable</option>
                      </select>
                    </div>
                    {quotationForm.vat_mode === 'avec_tva' ? (
                      <>
                        <div className="form-row">
                          <label>Code TVA</label>
                          <input
                            type="text"
                            value={quotationForm.vat_code}
                            onChange={(event) => handleQuotationFormChange('vat_code', event.target.value)}
                            placeholder="Code communiqué par l’entreprise"
                            required
                          />
                        </div>
                        <div className="form-row">
                          <label>Taux TVA (%)</label>
                          <input
                            type="number"
                            min={0.01}
                            max={100}
                            step={0.01}
                            value={quotationForm.vat_rate}
                            onChange={(event) => handleQuotationFormChange('vat_rate', event.target.value)}
                            placeholder="Taux applicable"
                            required
                          />
                        </div>
                      </>
                    ) : null}
                    <div className="form-row">
                      <label>Mode de règlement</label>
                      <input
                        type="text"
                        value={quotationForm.payment_method}
                        onChange={(event) => handleQuotationFormChange('payment_method', event.target.value)}
                        placeholder="Ex. virement bancaire"
                      />
                    </div>
                    <div className="form-row full-width">
                      <label>Échéance / modalités de règlement</label>
                      <input
                        type="text"
                        value={quotationForm.payment_terms}
                        onChange={(event) => handleQuotationFormChange('payment_terms', event.target.value)}
                        placeholder="Saisir les modalités convenues"
                      />
                    </div>
                  </div>

                  <div className="form-section">
                    <div className="form-section-header">
                      <h4>Articles</h4>
                      <button type="button" className="outline-btn" onClick={handleAddArticle}>
                        Ajouter un article
                      </button>
                    </div>
                    <div className="article-table">
                      <div className="article-table-head">
                        <span>Désignation *</span>
                        <span>Quantité *</span>
                        <span>Unité</span>
                        <span>PU *</span>
                        <span>Total</span>
                        <span></span>
                      </div>
                      {quotationForm.articles.map((article, index) => (
                        <div key={index} className="article-table-row">
                          <input
                            value={article.designation}
                            onChange={(event) => handleArticleChange(index, 'designation', event.target.value)}
                            placeholder="Désignation"
                            required
                          />
                          <input
                            type="number"
                            min={0.01}
                            step={0.01}
                            value={article.quantity}
                            onChange={(event) => handleArticleChange(index, 'quantity', event.target.value)}
                            required
                          />
                          <input
                            type="text"
                            value={article.unit}
                            onChange={(event) => handleArticleChange(index, 'unit', event.target.value)}
                            placeholder="Unité"
                          />
                          <input
                            type="number"
                            min={0}
                            step={0.01}
                            value={article.unit_price}
                            onChange={(event) => handleArticleChange(index, 'unit_price', event.target.value)}
                            required
                          />
                          <span>{formatCurrency(article.line_total)}</span>
                          <button type="button" className="icon-button" onClick={() => handleRemoveArticle(index)}>
                            <span className="material-symbols-outlined">delete</span>
                          </button>
                        </div>
                      ))}
                    </div>
                    {(() => {
                      const totalHT = quotationForm.articles.reduce(
                        (sum, article) => sum + calculateArticleLineTotal(article),
                        0,
                      )
                      const rate = Number(quotationForm.vat_rate)
                      const vatAmount =
                        quotationForm.vat_mode === 'avec_tva' && Number.isFinite(rate)
                          ? Math.round((totalHT * rate / 100 + Number.EPSILON) * 100) / 100
                          : 0
                      return (
                        <div className="form-row full-width">
                          <label>Récapitulatif du devis</label>
                          <div className="quotation-total">
                            Total HT : {formatCurrency(totalHT)}
                            <br />
                            TVA : {formatCurrency(vatAmount)}
                            <br />
                            Total TTC : {formatCurrency(totalHT + vatAmount)}
                          </div>
                        </div>
                      )
                    })()}
                  </div>

                  <div className="drawer-actions">
                    <button type="button" className="secondary-btn" onClick={() => setQuotationFormOpen(false)}>
                      Annuler
                    </button>
                    <button type="submit" className="primary-btn">
                      {quotationFormMode === 'edit' ? 'Mettre à jour le devis' : 'Créer le devis'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : null}
        </section>
      )
    }

    if (activePage === 'roles') {
      return (
        <section className="role-management-panel page-card">
          <div className="role-management-header">
            <div>
              <span className="role-management-eyebrow">ADMINISTRATION</span>
              <h3>Rôles</h3>
              <p>Gestion des rôles des comptes existants.</p>
            </div>
            <span className="role-management-count">{filteredUsers.length} compte(s)</span>
          </div>
          <div className="role-account-grid">
            {filteredUsers.length > 0 ? (
              filteredUsers.map((user) => {
                const rolePresentation = getRolePresentation(user.role)
                const initials = (user.full_name || user.email)
                  .split(' ')
                  .map((part) => part[0])
                  .join('')
                  .slice(0, 2)
                  .toUpperCase()

                return (
                  <article key={user.id} className="role-account-card">
                    <div className="role-account-topline">
                      <span className={`role-account-avatar ${rolePresentation.className}`}>{initials}</span>
                      <span className={`role-pill ${rolePresentation.className}`}>{rolePresentation.label}</span>
                    </div>
                    <div className="role-account-identity">
                      <strong>{user.full_name || user.email}</strong>
                      <span>{user.email}</span>
                    </div>
                    <label className="role-account-label" htmlFor={`role-${user.id}`}>Rôle actuel</label>
                    <select
                      id={`role-${user.id}`}
                      className="role-account-select"
                      value={user.role}
                      onChange={(event) => handleRoleChange(user, event.target.value)}
                    >
                      <option value="COLLABORATEUR">Collaborateur</option>
                      <option value="RESPONSABLE">Responsable</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </article>
                )
              })
            ) : (
              <div className="role-account-empty">Aucun compte correspondant.</div>
            )}
          </div>
        </section>
      )
    }

    if (activePage === 'reports') {
      return (
        <section className="page-card report-grid">
          <div className="chart-panel">
            <div className="panel-header">
              <div>
                <h3>Rapport des devis</h3>
                <p>Données réelles agrégées par mois.</p>
              </div>
            </div>
            {filteredChart.length > 0 ? (
              <div className="chart-bars">
                {filteredChart.map((point) => (
                  <div key={point.label} className="chart-bar-group">
                    <div className="chart-bar-value">{point.value}</div>
                    <div className="chart-bar-track">
                      <div className="chart-bar-fill" style={{ height: `${Math.max(point.value, 1)}%` }} />
                    </div>
                    <div className="chart-bar-label">{point.label}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </section>
      )
    }

    if (activePage === 'settings') {
      return (
        <section className="page-card">
          <div className="panel-header">
            <div>
              <h3>Paramètres</h3>
              <p>Informations du compte et sécurité de votre accès.</p>
            </div>
          </div>

          <div className="settings-layout">
            <div className="settings-card">
              <div className="section-title-row">
                <span className="material-symbols-outlined">person</span>
                <h4>Informations du compte</h4>
              </div>

              <div className="settings-list">
                <div className="settings-row">
                  <span>Nom et prénom</span>
                  <strong>{currentUser.full_name || 'Non renseigné'}</strong>
                </div>
                <div className="settings-row">
                  <span>Adresse e-mail</span>
                  <strong>{currentUser.email}</strong>
                </div>
                <div className="settings-row">
                  <span>Rôle</span>
                  <strong>{getRoleLabel(currentUser.role)}</strong>
                </div>
              </div>
            </div>

            <div className="settings-card">
              <div className="section-title-row">
                <span className="material-symbols-outlined">security</span>
                <h4>Sécurité</h4>
              </div>

              <form className="security-form" onSubmit={handlePasswordSubmit} noValidate>
                <div className="field-group">
                  <label htmlFor="old-password">Ancien mot de passe</label>
                  <div className="input-wrap">
                    <span className="input-icon material-symbols-outlined">lock</span>
                    <input
                      id="old-password"
                      type="password"
                      value={passwordForm.old_password}
                      onChange={handlePasswordFieldChange('old_password')}
                      placeholder="Ancien mot de passe"
                    />
                  </div>
                </div>

                <div className="field-group">
                  <label htmlFor="new-password">Nouveau mot de passe</label>
                  <div className="input-wrap">
                    <span className="input-icon material-symbols-outlined">key</span>
                    <input
                      id="new-password"
                      type="password"
                      value={passwordForm.new_password}
                      onChange={handlePasswordFieldChange('new_password')}
                      placeholder="Nouveau mot de passe"
                    />
                  </div>
                </div>

                <div className="field-group">
                  <label htmlFor="confirm-password">Confirmation du nouveau mot de passe</label>
                  <div className="input-wrap">
                    <span className="input-icon material-symbols-outlined">verified_user</span>
                    <input
                      id="confirm-password"
                      type="password"
                      value={passwordForm.confirm_password}
                      onChange={handlePasswordFieldChange('confirm_password')}
                      placeholder="Confirmer le nouveau mot de passe"
                    />
                  </div>
                </div>

                {passwordStatus ? (
                  <p className={passwordStatus.type === 'success' ? 'success-message' : 'form-error'}>{passwordStatus.message}</p>
                ) : null}

                <button type="submit" className="primary-btn" disabled={isPasswordSubmitting}>
                  {isPasswordSubmitting ? 'Modification...' : 'Modifier le mot de passe'}
                </button>
              </form>
            </div>
          </div>
        </section>
      )
    }

    if (activePage === 'help') {
      return (
        <section className="page-card help-page">
          <div className="panel-header">
            <div className="help-page-header">
              <p>Informations utiles sur le fonctionnement de ProQuote ERP.</p>
            </div>
          </div>

          <div className="help-content">
            <div className="help-section help-section--primary">
              <div className="help-section-header">
                <h4>Fonctionnement des statuts</h4>
              </div>

              <div className="status-flow-block">
                <div className="flow-subtitle">Parcours normal</div>
                <div className="status-flow" aria-label="Parcours normal des statuts des devis">
                  <div className="flow-step pending">DEVIS CRÉÉ</div>
                  <span className="flow-arrow" aria-hidden="true">→</span>
                  <div className="flow-step pending">EN ATTENTE</div>
                  <span className="flow-arrow" aria-hidden="true">→</span>
                  <div className="flow-step sent">ENVOYÉ</div>
                  <span className="flow-arrow" aria-hidden="true">→</span>
                  <div className="flow-step sent">RETOUR DU CLIENT PAR E-MAIL</div>
                  <span className="flow-arrow" aria-hidden="true">→</span>
                  <div className="flow-step approved">VALIDÉ / ANNULÉ</div>
                </div>
              </div>

              <div className="status-flow-block status-flow-block--secondary">
                <div className="flow-subtitle">Cas supplémentaire</div>
                <div className="status-flow secondary-flow" aria-label="Cas d'expiration d'un devis">
                  <div className="flow-step sent">ENVOYÉ</div>
                  <span className="flow-arrow" aria-hidden="true">→</span>
                  <div className="flow-step expired">EXPIRÉ</div>
                </div>
              </div>

              <div className="help-copy">
                <p><strong>Parcours normal :</strong> DEVIS CRÉÉ → EN ATTENTE → ENVOYÉ → RETOUR DU CLIENT PAR E-MAIL → VALIDÉ ou ANNULÉ</p>
              </div>
            </div>

            <div className="help-section">
              <div className="help-section-header">
                <h4>Signification des statuts</h4>
              </div>

              <div className="status-definition-list">
                <div className="status-item">
                  <span className="status-pill pending">EN ATTENTE</span>
                  <p>Un devis créé dans le système est initialement considéré comme un brouillon et possède le statut « En attente ».</p>
                </div>

                <div className="status-item">
                  <span className="status-pill sent">ENVOYÉ</span>
                  <p>Lorsque le devis est envoyé avec succès au client à une adresse e-mail existante, son statut devient « Envoyé ».</p>
                </div>

                <div className="status-item">
                  <span className="status-pill approved">VALIDÉ</span>
                  <p>Le client répond à l’entreprise par e-mail pour confirmer son accord. L’Administrateur ou le Manager met ensuite manuellement le statut du devis à « Validé », selon ses droits.</p>
                </div>

                <div className="status-item">
                  <span className="status-pill cancelled">ANNULÉ</span>
                  <p>Le client répond à l’entreprise par e-mail pour refuser le devis. L’Administrateur ou le Manager met ensuite manuellement le statut du devis à « Annulé », selon ses droits.</p>
                </div>

                <div className="status-item">
                  <span className="status-pill expired">EXPIRÉ</span>
                  <p>Le délai de validité du devis arrive à échéance. Le devis passe alors au statut « Expiré ».</p>
                </div>
              </div>
            </div>

            <div className="help-section" id="mentions-legales">
              <div className="help-section-header">
                <h4>Interaction avec le client</h4>
              </div>

              <div className="callout-box">
                <strong>Le client n’interagit pas directement avec ProQuote ERP.</strong>
              </div>

              <div className="access-flow" aria-label="Processus d'interaction avec le client">
                <div className="access-step">ProQuote ERP</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Envoi du devis par e-mail</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Client</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Réponse du client par e-mail</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Administrateur ou Manager</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Mise à jour du statut</div>
              </div>
            </div>

            <div className="help-section" id="confidentialite">
              <div className="help-section-header">
                <h4>Gestion des accès</h4>
              </div>

              <div className="access-flow" aria-label="Parcours de demande d'accès">
                <div className="access-step">Demande d’accès</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Coordonnées + rôle souhaité</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Envoi de la demande</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Validation par l’Administrateur</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Accès accordé</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Connexion</div>
                <span className="flow-arrow" aria-hidden="true">→</span>
                <div className="access-step">Dashboard selon le rôle</div>
              </div>

              <ul className="help-list">
                <li>La personne ne peut pas accéder au Dashboard avant l’accord de l’Administrateur.</li>
                <li>L’Administrateur est responsable de l’accord d’accès.</li>
                <li>Le rôle demandé est soumis à la validation de l’Administrateur.</li>
                <li>Les mots de passe sont enregistrés sous forme de hachage et ne sont pas retournés par les API.</li>
                <li>Les accès aux devis, historiques, articles, relances et PDF sont contrôlés côté backend selon le rôle et le propriétaire du devis.</li>
                <li>Les sessions utilisent des jetons expirants et révocables lors de la déconnexion ou d’un changement de mot de passe.</li>
              </ul>
            </div>

            <div className="help-section" id="support-technique">
              <div className="help-section-header">
                <h4>Problèmes et assistance</h4>
              </div>

              <div className="issue-grid">
                <div className="issue-block">
                  <h5>Problème d’envoi d’e-mail</h5>
                  <p>Vérifier que l’adresse e-mail du client existe et qu’elle est correctement renseignée.</p>
                </div>

                <div className="issue-block">
                  <h5>Assistance technique</h5>
                  <p>
                    Consultez la <a href="/support-technique">page Support technique</a> pour les
                    consignes sur les devis, les PDF et les accès. Aucun contact dédié n’est
                    configuré dans l’application.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )
    }

  }

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="sidebar-inner">
          <div className="sidebar-brand">
            <div className="brand-badge">
              <img src={logo} alt="Logo Trident Oil Services" />
            </div>
            <div>
              <h1>ProQuote ERP</h1>
              <p>{isManager ? 'Trident Oil Services' : 'Gestion d’Entreprise'}</p>
            </div>
          </div>

          <nav className="sidebar-nav" aria-label="Navigation principale">
            {visiblePages.map((page) => (
              <button key={page} type="button" className={`nav-item ${activePage === page ? 'active' : ''}`} onClick={() => openPage(page)}>
                <span className="material-symbols-outlined">{adminPageIcons[page]}</span>
                <span>{pageLabels[page]}</span>
              </button>
            ))}
          </nav>

          <div className="sidebar-footer">
            <button type="button" className="nav-item logout" onClick={() => { void onLogout() }}>
              <span className="material-symbols-outlined">logout</span>
              <span>Déconnexion</span>
            </button>
          </div>
        </div>
      </aside>

      <header className="dashboard-header">
        <div className="header-title-wrap">
          <button
            type="button"
            className="mobile-menu-button"
            onClick={() => openPage(visiblePages[0] as AdminPage)}
          >
            <span className="material-symbols-outlined">menu</span>
          </button>
          <h2>{pageLabels[activePage]}</h2>
        </div>

        <div className="header-tools">
          <div className="global-search">
            <span className="material-symbols-outlined">search</span>
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>

          <div className="header-actions">
            <div className="divider" />
            <div className="user-pill user-pill-button">
              <button
                type="button"
                className="avatar-button"
                onClick={handleAvatarPicker}
                aria-label={`Modifier la photo de profil de ${currentUser.full_name || currentUser.email}`}
              >
                {currentUser.avatar_url ? (
                  <img src={currentUser.avatar_url} alt={`Photo de profil de ${currentUser.full_name || currentUser.email}`} />
                ) : (
                  <span className="avatar-fallback">
                    {currentUser.full_name
                      ? currentUser.full_name
                          .split(' ')
                          .map((segment) => segment[0]?.toUpperCase())
                          .slice(0, 2)
                          .join('')
                      : currentUser.email?.charAt(0).toUpperCase()}
                  </span>
                )}
              </button>
              <span>{currentUser.full_name || currentUser.email}</span>
            </div>
            <input ref={avatarInputRef} type="file" accept="image/*" className="hidden-file-input" onChange={handleAvatarChange} />
          </div>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="dashboard-container">
          {statusMessage ? <p className="success-message dashboard-message">{statusMessage}</p> : null}
          {errorMessage ? <p className="form-error dashboard-message">{errorMessage}</p> : null}
          {activePage === 'dashboard' && !dashboardDataLoaded ? (
            <p className="dashboard-message" role={loading ? 'status' : 'alert'}>
              {loading ? 'Chargement des données du tableau de bord…' : 'Les données du tableau de bord ne sont pas disponibles.'}
            </p>
          ) : renderCurrentPage()}
          {activePage !== 'dashboard' && activePage !== 'roles' ? <div className="table-footer search-footer"><span>{renderSearchResultsCount()}</span></div> : null}
        </div>
      </main>
    </div>
  )
}

export default App
