from celery import shared_task
from .models import AchatProduit

@shared_task
def generer_revenus_journaliers():
    """"Génèrer les revenus journaliers uniquement pour les produits actifs"""
    achats_actifs = AchatProduit.objects.filter(statut='actif')
    for achat in achats_actifs:
        achat.generer_revenu_journalier()

@shared_task
def verifier_expirations():
    """"Vérifie et marque les achats expirés"""
    achats_actifs = AchatProduit.objects.filter(statut='actif')
    for achat in achats_actifs:
        achat.verifier_date()