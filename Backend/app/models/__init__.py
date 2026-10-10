"""Package des modèles persistés de l'application."""

# Importer les modèles dans un ordre stable pour que les relations
# SQLAlchemy résolvent les classes associées avant les mappers ne soient
# configurés.
from app.models.article import Article  # noqa: F401
from app.models.quotation import Quotation  # noqa: F401
