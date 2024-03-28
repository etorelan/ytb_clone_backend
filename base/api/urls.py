from django.urls import path
from .views import *

urlpatterns = [
    path("video-upload/", view=video_upload, name="video_upload"),
    path("<str:video_id>/", view=get_video, name="get_video"),
    path("thumbnails/<str:image>/", view=get_image, name="get_image"),
    path("description/<str:video_id>/", view=get_description, name="get_description"),
    path("search-bar", get_search_options, name="get_search_bar_options"),
    path("subscribe", subscribe, name="subscribe"),
    path("like", like, name="like"),
    path("like-info",get_like_info, name="get_like_info"),
    path("like-comment", like_comment, name="comment"),
    path("subscriptions", subscriptions, name="subscriptions")
]