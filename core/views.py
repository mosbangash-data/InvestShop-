from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import login
from .models import Profil, Produit, AchatProduit, Depot, Retrait, CommissionParrainage, ParametrePaiement, RevenuJournalier
from .forms import AchatProduitForm, DepotForm, RetraitForm, RegisterForm
from django.db.models import Sum
from decimal import Decimal
from django.db import transaction

def home(request):
    return render(request, "core/auth/home.html")

def register(request):

    ref = request.GET.get('ref')

    if request.method == 'POST':
        form = RegisterForm(request.POST, initial={"code_parrain": ref})

        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.set_password(form.cleaned_data["password1"])
            user.save()

            profil = Profil.objects.create(user=user)
            code_parrain = form.cleaned_data.get('code_parrain')

            if code_parrain:
                try:
                    parrain = Profil.objects.get(code_parrainage=code_parrain)
                    profil.parrain = parrain
                    profil.save()
                except Profil.DoesNotExist:
                    messages.warning(request,"Code parrain invalide")

            login(request,user)
            messages.success(request,"Compte créé avec succès")

            return redirect('dashboard')
        else:
            print(form.errors)
    else:
        form = RegisterForm(initial={'code_parrain': ref})

    return render(request,'core/auth/register.html',{'form':form, 'ref': ref})

#DASHBOARD CLIENT

@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect ('admin_dashboard')
    
    profil = Profil.objects.get(user=request.user)
    achats = AchatProduit.objects.filter(profil=profil)
    for achat in achats.filter(statut='actif'):
        achat.verifier_date()
        achat.generer_revenu_journalier_auto()

    depots = Depot.objects.filter(profil=profil).order_by('-date')
    retraits = Retrait.objects.filter(profil=profil).order_by('-date')
    commissions = CommissionParrainage.objects.filter(parrain=profil).order_by('-date')
    total_depots = depots.filter(statut="valide").aggregate(total=Sum("montant")).get("total") or Decimal('0')  
    total_retraits = retraits.filter(statut="valide").aggregate(total=Sum("montant")).get("total") or Decimal('0') 
    total_commissions = commissions.aggregate(total=Sum("montant")).get("total") or Decimal('0') 

    produits_actifs = achats.filter(statut='actif').count()
    produits_expires = achats.filter(statut='expire').count()
    revenus = RevenuJournalier.objects.filter(achat__profil=profil)

    total_revenus = revenus.aggregate(total=Sum("montant")).get("total") or 0

    context = {
        'profil': profil,
        'achats': achats,
        'depots': depots,
        'retraits': retraits,
        'commissions': commissions,
        'total_depots': total_depots,
        'total_retraits': total_retraits,
        'total_commission': total_commissions,
        'produits_actifs': produits_actifs,
        'produits_expires': produits_expires,
        'total_revenus': total_revenus,
    }
    return render(request, 'core/dashboard/dashboard.html', context)

# LISTE DES PRODUIT
@login_required
def liste_produits(request):
    produits = Produit.objects.all()
    context = {'produits': produits}

    return render(request, 'core/produits/liste.html', context)

#DETAIL PRODUIT +ACHAT
@login_required
def detail_produit(request, produit_id):
    profil = Profil.objects.get(user=request.user)
    produit = get_object_or_404(Produit, id=produit_id)

    if request.method == 'POST':
        form = AchatProduitForm(profil=profil, produit=produit, data=request.POST)
        try:
            form.save()
            messages.success(request, f"Produit {produit.nom} acheté avec succès")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, str(e))
    else: 
        form = AchatProduitForm()
    
    context = {
        'produit': produit,
        'form': form
    }
    return render(request, 'core/produits/detail.html', context)

#DEPOT
@login_required
def depot(request):
    parametre = ParametrePaiement.objects.first()
    profil = Profil.objects.get(user=request.user)

    if request.method == "POST":
        form = DepotForm(request.POST, request.FILES, profil=profil)
        if form.is_valid():
            depot = form.save(commit=False)
            depot.numero_compte = parametre.numero_paiement
            depot.moyen_de_paiement = parametre.nom_methode
            depot.save()
            messages.success(request, "Votre demande de dépôt a été faite avec succès !")
            return redirect('dashboard')
        else:
            print(form.errors)
    else:
        form = DepotForm()

    context = {
        'form': form,
        'moyen_de_paiement': parametre.nom_methode,
        'numero_compte': parametre.numero_paiement,
        'nom_compte': parametre.nom_compte,
    }

    return render(request, 'core/transactions/depot.html', context)
    
#RETRAIT
from django.db import transaction

@login_required
def retrait(request):

    profil = request.user.profil
    if request.method == "POST":
        form = RetraitForm(request.POST, profil=profil)
        if form.is_valid():
            montant = form.cleaned_data["montant"]
            try:
                with transaction.atomic():
                    profil = Profil.objects.select_for_update().get(id=profil.id)

                    if profil.solde < montant:
                        messages.error(request, "Solde insuffisant")
                        return redirect("retrait")

                    retrait = form.save(commit=False)
                    retrait.profil = profil

                    # Bloquer le solde immédiatement
                    profil.solde -= montant
                    profil.save()

                    retrait.save()

                messages.success(request, "Votre demande de retrait a été envoyée")
                return redirect("dashboard")

            except Exception:
                messages.error(request, "Erreur lors de la demande")

    else:
        form = RetraitForm(profil=profil)

    return render(request, "core/transactions/retrait.html", {"form": form})

#----------PARRAINAGE -------------------
def parrainage(request):
    profil = Profil.objects.get(user=request.user)
    filleuls = Profil.objects.filter(parrain=profil)
    domain = request.build_absolute_uri("/")[:-1]
    referral_link = f"{domain}/register/?ref={profil.code_parrainage}"

    context = {
        'profil': profil,
        'filleuls': filleuls,
        'referral_link': referral_link,
    }
    return render(request, 'core/auth/parrainage.html', context)

# ADMIN CHECK
def is_admin(user):
    return user.is_staff

#ADMIN DASHBOARD
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    depots = Depot.objects.filter(statut='en_attente')
    retraits = Retrait.objects.filter(statut='en_attente')
    utilisateurs = Profil.objects.all()
    produits = Produit.objects.all()
    total_depots = sum(d.montant for d in Depot.objects.filter(statut='valide'))
    total_retraits = sum(r.montant for r in Retrait.objects.filter(statut='valide'))
    total_commissions = sum(c.montant for c in CommissionParrainage.objects.all())
    solde_global = sum(u.solde for u in Profil.objects.all())

    context = {
        'depots': depots,
        'retraits': retraits,
        'utilisateurs': utilisateurs,
        'produits': produits,
        'total_depots': total_depots,
        'total_retraits': total_retraits,
        'total_commissions': total_commissions,
        'solde_global': solde_global,
    }
    return render(request, 'core/dashboard/admin_dashboard.html', context)

# VALIDER DEPOT
@login_required
@user_passes_test(is_admin)
@transaction.atomic
def valider_depot(request, depot_id):
    depot = Depot.objects.select_for_update().get(id=depot_id)
    
    if depot.statut != "en_attente":
        messages.warning(request, "Ce dépot a déjà été traité.")
        return redirect('admin_dashboard')
    
    depot.statut = "valide"
    depot.save()

    profil = depot.profil
    profil.solde += depot.montant
    profil.save()

    if profil.parrain and not profil.bonus_parrainage_deja_donne:
        nb_depots_valides = Depot.objects.filter(
            profil=profil,
            statut="valide"
        ).count()

        if nb_depots_valides == 1:
            commisssion = depot.montant * Decimal('0.03')
            CommissionParrainage.objects.create(
                parrain=profil.parrain,
                filleul=profil,
                montant=commisssion
            )

            parrain = profil.parrain
            parrain.solde += commisssion
            parrain.save()

            profil.bonus_parrainage_deja_donne = True

            profil.save()
    
    messages.success(request, "Dépot validé avec succès.")
    return redirect('admin_dashboard')

#VALIDER RETRAIT
@login_required
@user_passes_test(is_admin)
def valider_retrait(request, retrait_id):

    with transaction.atomic():

        retrait = Retrait.objects.select_for_update().get(id=retrait_id)

        if retrait.statut != "en_attente":
            messages.warning(request, "Ce retrait a déjà été traité.")
            return redirect("admin_dashboard")

        retrait.statut = "valide"
        retrait.save()

    messages.success(request, "Retrait validé avec succès.")
    return redirect("admin_dashboard")
#----------REFUSER RETRAIt--------------
@login_required
@user_passes_test(is_admin)
def refuser_retrait(request, retrait_id):

    with transaction.atomic():

        retrait = Retrait.objects.select_for_update().get(id=retrait_id)

        if retrait.statut != "en_attente":
            messages.warning(request, "Ce retrait a déjà été traité.")
            return redirect("admin_dashboard")

        profil = retrait.profil

        # remboursement
        profil.solde += retrait.montant
        profil.save()

        retrait.statut = "refuse"
        retrait.save()

    messages.success(request, "Retrait refusé et solde remboursé.")
    return redirect("admin_dashboard")

#--------------------REFUSER DEPOT-------------------
@login_required
@user_passes_test(is_admin)
def refuser_depot(request, depot_id):
    with transaction.atomic():

        depot = Depot.objects.select_for_update().get(id=depot_id)

        if depot.statut != "en_attente":
            messages.warning(request, "Ce depot a déjà été traité.")
            return redirect("admin_dashboard")

        profil = depot.profil

        # remboursement
        profil.solde += depot.montant * 0
        profil.save()

        depot.statut = "refuse"
        depot.save()

    messages.success(request, "Dépot refusé.")
    return redirect("admin_dashboard")

from django.contrib.auth.models import User
from django.http import HttpResponse
