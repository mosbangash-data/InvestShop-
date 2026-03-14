from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid

# ==============================
# Profil utilisateur
# ==============================
class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    parrain = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name='filleuls')
    code_parrainage = models.CharField(max_length=20, unique=True, blank=True)
    bonus_parrainage_deja_donne = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code_parrainage:
            self.code_parrainage = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# ==============================
# Paramètre paiement
# ==============================
class ParametrePaiement(models.Model):
    nom_methode = models.CharField(max_length=50)
    numero_paiement = models.CharField(max_length=50)
    nom_compte = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.nom_methode} - {self.numero_paiement} - {self.nom_compte}"

# ==============================
# Produit
# ==============================
class Produit(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=12, decimal_places=2)
    revenu_journalier = models.DecimalField(max_digits=12, decimal_places=2)
    duree_jours = models.PositiveIntegerField(default=90)
    photo = models.ImageField(upload_to='produits/')
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

# ==============================
# Achat Produit
# ==============================
class AchatProduit(models.Model):
    STATUT_CHOICES =[
        ('actif', 'Actif'),
        ('expire', 'Expiré')
    ]
    profil = models.ForeignKey(Profil, on_delete=models.CASCADE, related_name="achats")
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    date_achat = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateField(blank=True, null=True)
    revenu_restant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    dernier_paiement = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.date_expiration:
            self.date_expiration = timezone.now() + timedelta(days=self.produit.duree_jours)
        super().save(*args, **kwargs)

    def verifier_date(self):
        if timezone.now().date() >= self.date_expiration:
            self.statut = "expire"
            self.save()

    def generer_revenu_journalier_auto(self):
        self.verifier_date()
        if self.statut != 'actif':
            return 0
        
        maintenant = timezone.now().date()
        date_debut = self.date_achat.date()
        dernier_paiement = self.dernier_paiement or date_debut
        jours_non_payes = (maintenant - dernier_paiement).days


        if jours_non_payes <=0 :
            return 0
        
        date_fin = date_debut + timedelta(days=self.produit.duree_jours)
        jours_restant = (date_fin - dernier_paiement).days
        jour_a_paye = min(jours_non_payes, jours_restant)

        if jour_a_paye <= 0:
            self.statut = 'expire'
            self.save()
            return 0

        revenu_total = self.produit.revenu_journalier * jour_a_paye

        for i in range(jour_a_paye):
            RevenuJournalier.objects.create(
                achat=self,
                montant=self.produit.revenu_journalier,
                date=dernier_paiement + timedelta(days=i+1)
            )

        self.profil.solde += self.produit.revenu_journalier
        self.profil.save()
            
        self.dernier_paiement = maintenant
        self.save()
        return revenu_total

    def __str__(self):
        return f"{self.profil.user.username} - {self.produit.nom}"

# ==============================
# Dépôt
# ==============================
class Depot(models.Model):
    STATUT_CHOICES = [
        ('en_attente','En attente'),
        ('valide','Validé'),
        ('refuse','Refusé'),
    ]
    profil = models.ForeignKey(Profil, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='en_attente')
    date = models.DateTimeField(auto_now_add=True)
    moyen_de_paiement = models.CharField(max_length=50)
    numero_compte = models.CharField(max_length=50)
    preuve_paiement = models.FileField(upload_to='preuves/')

    def __str__(self):
        return f"{self.profil.user.username} - {self.montant} FC"

# ==============================
# Retrait
# ==============================
class Retrait(models.Model):
    STATUT_CHOICES = [
        ('en_attente','En attente'),
        ('valide','Validé'),
        ('refuse','Refusé'),
    ]
    profil = models.ForeignKey(Profil, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    frais = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    montant_final = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    numero_reception = models.CharField(max_length=50)
    nom_compte = models.CharField(max_length=50)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='en_attente')
    date = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        self.frais = self.montant * Decimal('0.08')
        self.montant_final = self.montant - self.frais
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profil.user.username} - {self.montant_final} ({self.statut})"

# ==============================
# Commission parrainage
# ==============================
class CommissionParrainage(models.Model):
    parrain = models.ForeignKey(Profil, on_delete=models.CASCADE, related_name="commissions_gagnees")
    filleul = models.ForeignKey(Profil, on_delete=models.CASCADE, related_name="commissions_generees")
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parrain.user.username} gagne {self.montant} FC de {self.filleul.user.username}"

# ==============================
# Revenu journalier automatique
# ==============================
class RevenuJournalier(models.Model):
    achat = models.ForeignKey(AchatProduit, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.achat.profil.user.username} - {self.montant} FC {self.date}"