from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from decimal import Decimal
from .models import Profil, Produit, AchatProduit, Depot, Retrait, ParametrePaiement, CommissionParrainage, RevenuJournalier

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'solde', 'bonus_parrainage_deja_donne', 'code_parrainage')
    search_fields = ('user__username', 'code_parrainage',)
    list_filter = ('bonus_parrainage_deja_donne',)
    readonly_fields = ('solde', 'code_parrainage')
    ordering = ('-id',)

@admin.register(ParametrePaiement)
class ParametrePaiementAdmin(admin.ModelAdmin):
    list_display = ('nom_methode', 'numero_paiement', 'nom_compte')
    search_fields = ('nom_methode', 'numero_paiement', 'nom_compte')

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prix', 'revenu_journalier', 'duree_jours', 'actif', 'date_creation', 'photo_tag')
    list_filter = ('actif',)
    search_fields = ('nom',)
    
    def photo_tag(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 50px; height:50px;" />'.format(obj.photo.url))
        return "-" 
    photo_tag.short_description = "photo"

@admin.register(AchatProduit)
class AchatProduitAdmin(admin.ModelAdmin):
    list_display = ('profil', 'produit', 'date_achat', 'statut')
    list_filter = ('statut',)
    search_fields = ('profil__user__username', 'produit__nom',)
    ordering = ('-date_achat',)

@admin.register(Depot)
class DepotAdmin(admin.ModelAdmin):
    list_display = ('profil', 'montant', 'statut', 'date', 'moyen_de_paiement')
    list_filter = ('statut',)
    search_fields = ('profil__user__username', 'numero_compte',)
    ordering = ('-date',)
        
    actions = ['valider_depot', 'refuser_depot']

    def valider_depot(self, request, queryset):
        for depot in queryset:
            if depot.statut != 'en_attente':
                messages.warning(request, f"Le dépot de {depot.profil.user.username} a deja été traité.")
                continue

            depot.statut='valide'
            depot.save()
            depot.profil.solde += depot.montant
            depot.profil.save()

            profil=depot.profil
            if profil.parrain and not profil.bonus_parrainage_deja_donne:
                nb_depots = Depot.objects.filter(profil=profil, statut="valide").count()
                if nb_depots == 1:
                    commission = depot.montant * Decimal('0.03')
                    profil.parrain.sode += commission
                    profil.save()

                    profil.bonus_parrainage_deja_donne = True
                    profil.save()
        messages.success(request, "Les dépots sélectionnés ont étés validés.")
    valider_depot.short_description = "Valider les dépots sélectionnés"

    def refuser_depot(self, request, queryset):
        for depot in queryset:
            profil = depot.profil
            if depot.statut == 'en_attente':
                depot.satut = 'refuse'
                depot.save()

                profil.solde += depot.montant * 0
                profil.save()
    refuser_depot.short_description = "Refuser les dépots sélectionnés"
            
    
@admin.register(Retrait)
class RetraitAdmin(admin.ModelAdmin):
    list_display = ('profil', 'montant', 'frais', 'montant_final', 'statut', 'date', 'numero_reception')
    list_filter = ('statut',)
    search_fields = ('profil__user__username', 'numero_reception')
    ordering = ('-date',)
        
    actions = ['valider_retrait', 'refuser_retrait']

    def valider_retrait(self, request, queryset):
        for retrait in queryset:
            profil = retrait.profil
            if retrait.statut != 'en_attente':
                messages.warning(request, f"Le retrait de {profil.user.username} a déjà été traité.")
                continue
            if profil.solde < retrait.montant:
                messages.error(request, f"Solde insuffisant pour {profil.user.username}")
                continue

            retrait.statut = 'valide'
            retrait.save()

            profil.solde -= retrait.montant
            profil.save()

        messages.success(request, "Les retraits sélectionnés ont étés validés avec succès.")
    valider_retrait.short_description = "Valider les retraits sélectionnés"

    def refuser_retrait(self, request, queryset):

        for retrait in queryset:

            if retrait.statut == "en_attente":

                profil = retrait.profil
                profil.solde += retrait.montant
                profil.save()

                retrait.statut = "refuse"
                retrait.save()
    refuser_retrait.short_description = "Refuser les retraits sélectionnés"

@admin.register(CommissionParrainage)
class CommissionParrainageAdmin(admin.ModelAdmin):
    list_display = (
        "parrain",
        "filleul",
        "montant",
        "date"
    )
    search_fields = (
        "parrain__user__username",
        "filleul__user__username",
    )
    ordering = ("-date",)

@admin.register(RevenuJournalier)
class RevenuJournalierAdmin(admin.ModelAdmin):
    list_display = ('achat', 'montant', 'date')
    search_fields = ('achat__profil__user__username',)