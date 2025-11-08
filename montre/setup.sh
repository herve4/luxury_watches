#!/bin/bash
echo "Installation des dependances Python..."
pip install -r requirements.txt

echo "Migrations de la base de donnees..."
python manage.py makemigrations
python manage.py migrate

echo "Installation des dependances npm..."
cd theme/static
npm install

echo "Compilation des assets..."
npm run build

echo "Collection des fichiers statiques..."
cd ../..
python manage.py collectstatic --noinput

echo "Configuration terminee avec succes!"
