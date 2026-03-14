from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Depot

class Command(BaseCommand):
    help = "Supprimer les preuves de paiement après deux jours"

    def handle(self, *args, **kwars):
        limite = timezone.now() - timedelta(days=2)
        depots = Depot.objects.filter(statut='valide', date__lte=limite)
        compteur = 0
        
        for depot in depots:
            if depot.preuve_paiement:
                depot.preuve_paiement.delete(save=False)

                depot.preuve_paiement = None
                depot.save()
                compteur += 1

        self.stdout.write(self.style.SUCCESS(f"{compteur} preuves de paiment supprimer"))       