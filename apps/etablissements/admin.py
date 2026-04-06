from django.contrib import admin
from .models import Etablissement, Cycle, Niveau, Serie, AnneeScolaire, JourFerie, RegimePedagogique


@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ['sigle', 'nom', 'email', 'is_active']
    search_fields = ['sigle', 'nom']


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ['etablissement', 'type_cycle', 'is_active']
    list_filter = ['type_cycle', 'etablissement']


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ['nom', 'cycle', 'ordre', 'is_active']
    list_filter = ['cycle__type_cycle', 'cycle__etablissement']


admin.site.register(Serie)
admin.site.register(AnneeScolaire)
admin.site.register(JourFerie)
admin.site.register(RegimePedagogique)
