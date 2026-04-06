from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Notification, TokenFCM
from .serializers import NotificationSerializer, TokenFCMSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(destinataire=self.request.user)
        non_lues = self.request.query_params.get('non_lues')
        if non_lues == '1':
            qs = qs.filter(lue=False)
        return qs


class MarquerLueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notif_pk):
        try:
            notif = Notification.objects.get(pk=notif_pk, destinataire=request.user)
        except Notification.DoesNotExist:
            return Response({'detail': 'Notification introuvable.'}, status=404)
        notif.lue = True
        notif.date_lecture = timezone.now()
        notif.save(update_fields=['lue', 'date_lecture'])
        return Response({'detail': 'Marquée comme lue.'})


class MarquerToutesLuesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            destinataire=request.user, lue=False
        ).update(lue=True, date_lecture=timezone.now())
        return Response({'detail': 'Toutes les notifications marquées comme lues.'})


class EnregistrerTokenFCMView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token requis.'}, status=400)
        TokenFCM.objects.update_or_create(
            token=token,
            defaults={'user': request.user}
        )
        return Response({'detail': 'Token FCM enregistré.'})
