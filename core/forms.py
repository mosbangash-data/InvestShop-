from django import forms
from .models import Depot, Retrait, AchatProduit
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    code_parrain = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "code_parrain"]

#Formulaire depot
class DepotForm(forms.ModelForm):
    class Meta:
        model = Depot
        fields = ["montant", "preuve_paiement"]

    def __init__(self, *args, **kwargs):
        self.profil = kwargs.pop("profil", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        depot = super().save(commit=False)
        if self.profil:
            depot.profil = self.profil
        if commit:
            depot.save()
        return depot

#Formulaire retrait
class RetraitForm(forms.ModelForm):
    class Meta:
        model = Retrait
        fields = ["montant", "numero_reception", "nom_compte"]

    def __init__(self, *args, **kwargs):
        self.profil = kwargs.pop("profil", None)
        super().__init__(*args, **kwargs)

    def clean_montant(self):
        montant = self.cleaned_data.get("montant")
        if montant < Decimal('12000'):
            raise ValidationError("Les montant minimum de retrait est de 12 000 FC")
        if self.profil and montant > self.profil.solde:
            raise ValidationError("Vous ne pouvez pas retirer plus que votre solde")
        
        return montant
        
#Formulaire achat produit
class AchatProduitForm(forms.ModelForm):
    class Meta:
        model = AchatProduit
        fields =[]

    def __init__(self, *args, **kwargs):
        self.profil = kwargs.pop("profil", None)
        self.produit = kwargs.pop("produit", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        if self.profil.solde < self.produit.prix:
            raise ValidationError("Solde insuffisant pour acheter ce produit")
        
        with transaction.atomic():
            self.profil.solde -= self.produit.prix
            self.profil.save()

            achat = AchatProduit(
                profil=self.profil,
                produit=self.produit,
                revenu_restant=self.produit.revenu_journalier * self.produit.duree_jours,
            )
            if commit:
                achat.save()
        return achat

