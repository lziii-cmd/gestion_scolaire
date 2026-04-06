from django.contrib import admin
from .models import TypeFrais, Frais, Paiement, Recu, ClotureCaisse


@admin.register(TypeFrais)
class TypeFraisAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'etablissement', 'montant_defaut', 'is_active']
    list_filter = ['etablissement', 'is_active']


@admin.register(Frais)
class FraisAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'type_frais', 'montant']
    search_fields = ['inscription__eleve__nom', 'inscription__eleve__prenom']


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'montant', 'date_paiement', 'caissier']
    list_filter = ['date_paiement']


admin.site.register(Recu)
admin.site.register(ClotureCaisse)
