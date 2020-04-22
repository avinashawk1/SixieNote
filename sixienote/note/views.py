from django.contrib.auth.models import User
from django.views.generic import CreateView, UpdateView, DeleteView, FormView
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import authenticate, login
from django_fsm import TransitionNotAllowed
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sixienote.note.serializers import NoteSerializer, UserSerializer
from .models import Note
from .mixins import LoginRequiredMixin, NoteMixin
from .forms import NoteForm


class NoteCreate(LoginRequiredMixin, NoteMixin, CreateView):
    form_class = NoteForm
    template_name = 'note/form.html'
    success_url = reverse_lazy('note:index')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.pub_date = timezone.now()
        return super(NoteCreate, self).form_valid(form)


class NoteUpdate(LoginRequiredMixin, NoteMixin, UpdateView):
    model = Note
    form_class = NoteForm
    template_name = 'note/form.html'
    success_url = reverse_lazy('note:index')

    def form_valid(self, form):
        form.instance.pub_date = timezone.now()
        return super(NoteUpdate, self).form_valid(form)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_user_or_403(self.object.owner)
        return super(NoteUpdate, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_user_or_403(self.object.owner)
        return super(NoteUpdate, self).post(request, *args, **kwargs)


class NoteDelete(LoginRequiredMixin, NoteMixin, DeleteView):
    model = Note
    success_url = reverse_lazy('note:index')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_user_or_403(self.object.owner)
        return super(NoteDelete, self).post(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, NoteMixin, FormView):
    template_name = 'note/profile.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('note:index')

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)

        return context

    def get_form_kwargs(self):
        """ Our form requires the user. """

        kwargs = super(ProfileView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def form_valid(self, form):
        form.save()

        username = self.request.user.username
        password = self.request.POST['new_password2']

        # If we don't re-authenticate with the new password the user will get logged out.
        user = authenticate(username=username, password=password)
        login(self.request, user)

        return super(ProfileView, self).form_valid(form)


class NoteViewSet(viewsets.ModelViewSet):
    """ List all of the notes for a user """
    permission_classes = (IsAuthenticated,)
    serializer_class = NoteSerializer

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user).order_by('-pub_date')

    @action(detail=True)
    def publish(self, request, pk=None):
        note = get_object_or_404(Note, pk=pk)
        try:
            note.publish()
            note.save()
        except TransitionNotAllowed as e:
            raise ValidationError(e)
        return Response({'status': 'published'})

    @action(detail=True)
    def retract(self, request, pk=None):
        note = get_object_or_404(Note, pk=pk)
        try:
            note.retract()
            note.save()
        except TransitionNotAllowed as e:
            raise ValidationError(e)
        return Response({'status': 'retracted'})


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = UserSerializer
