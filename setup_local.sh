#!/bin/bash
# Script d'installation locale pour Veille LinkedIn

echo "=== Installation Veille LinkedIn ==="

# Verifier Python
if ! command -v python3 &> /dev/null; then
    echo "ERREUR: Python 3 n'est pas installe"
    exit 1
fi

echo "Python detecte: $(python3 --version)"

# Creer environnement virtuel
echo "Creation environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Installer dependances
echo "Installation dependances..."
pip install -r requirements.txt

# Creer dossiers
echo "Creation dossiers data/ et logs/..."
mkdir -p data logs

# Copier .env si n'existe pas
if [ ! -f .env ]; then
    echo "Creation fichier .env depuis template..."
    cp config/.env.example .env
    echo ""
    echo "*** IMPORTANT: Edite .env avec tes credentials avant de lancer ***"
fi

# Init DB
echo "Initialisation base de donnees..."
python3 -c "
import sys; sys.path.insert(0, '.')
from src.database import init_db
init_db()
"

echo ""
echo "=== Installation terminee ==="
echo ""
echo "Prochaines etapes:"
echo "  1. Edite .env avec tes credentials"
echo "  2. Active le venv:  source venv/bin/activate"
echo "  3. Lance le scan:   python src/main.py"
echo ""
