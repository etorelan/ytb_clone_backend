import os, json, subprocess
from firebase_admin import firestore, auth, initialize_app, credentials

from datetime import datetime, timedelta

from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import get_object_or_404

from wsgiref.util import FileWrapper

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from django.views.decorators.http import require_GET
from django.views.decorators.gzip import gzip_page
from django.utils.http import http_date

from tempfile import NamedTemporaryFile

from base.models import *


LOAD_VIDEOS_PER_PAGE = 18
MAX_VIDEO_SIZE = 20 * 1024 * 1024
MAX_VIDEO_SIZE_STR = "20 MB"

SERVICE_ACCOUNT_FILE = json.loads(os.getenv('FIREBASE_CREDENTIALS'))
cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
initialize_app(cred)

# Now you can use firestore.client() to get the Firestore client
db = firestore.client()


@api_view(["POST"])
def video_upload(request):
    if request.FILES.get("video"):
        video_file = request.FILES["video"]
        thumbnail_file = request.FILES["thumbnail"]
        input_file_content = video_file.read()

        video_title = request.data.get("videoTitle")
        video_description = request.data.get("videoDescription")

        if video_file.size > MAX_VIDEO_SIZE:
            return JsonResponse({"message": f"Maximal video size is {MAX_VIDEO_SIZE_STR}"}, status=400)
        if (
            len(video_title) > MAX_VIDEO_TITLE_LENGTH
            or len(video_description) > MAX_VIDEO_DESCRIPTION_LENGTH
        ):
            return JsonResponse({"message": "Video text too long"}, status=400)

        with NamedTemporaryFile(suffix=".webp", delete=False) as temp_thumbnail_file:
            temp_thumbnail_file.write(thumbnail_file.read())

        with NamedTemporaryFile(suffix=".mp4", delete=False) as temp_input_file:
            temp_input_file.write(input_file_content)

        with NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output_file:
            # convert the video to .mp4 format with 360p quality
            ffmpeg_command = f'ffmpeg -y -i "{temp_input_file.name}" -vf "scale=640:360" -c:v libx264 -c:a aac "{temp_output_file.name}"'

            try:
                if ProcessedVideo.objects.filter(video_title=video_title).exists():
                    return JsonResponse(
                        {"message": "Video title not unique"}, status=400
                    )

                thumbnail_webp_file = NamedTemporaryFile(delete=False, suffix=".webp")
                ffmpeg_thumbnail_command = f'ffmpeg -y -i "{temp_thumbnail_file.name}" -vf "scale=640:360" "{thumbnail_webp_file.name}"'
                subprocess.run(ffmpeg_thumbnail_command, shell=True, check=True)

                subprocess.run(ffmpeg_command, shell=True, check=True)

                converted_video = ProcessedVideo()
                converted_video.video_title = video_title
                converted_video.video_description = video_description
                converted_video.thumbnail_file.save(
                    name="thumbnail.webp", content=thumbnail_webp_file, save=False
                )
                converted_video.video_file.save(
                    name="video.mp4", content=temp_output_file, save=False
                )
                converted_video.full_clean()
                converted_video.save()

                temp_input_file.close()
                temp_output_file.close()
                thumbnail_webp_file.close()

                os.remove(thumbnail_webp_file.name)
                os.remove(temp_thumbnail_file.name)
                os.remove(temp_input_file.name)
                os.remove(temp_output_file.name)

                return JsonResponse(
                    {
                        "message": "Upload successful! 🎉",
                        "videoId": converted_video.pk,
                        "thumbnail": converted_video.thumbnail_file.name,
                    },
                    status=200,
                )
            except subprocess.CalledProcessError:
                temp_input_file.close()
                temp_output_file.close()
                thumbnail_webp_file.close()

                os.remove(thumbnail_webp_file.name)
                os.remove(temp_thumbnail_file.name)
                os.remove(temp_input_file.name)
                os.remove(temp_output_file.name)

                return JsonResponse({"message": "Video conversion failed"}, status=500)

    return JsonResponse({"message": "No video file uploaded"}, status=400)


@api_view(["GET"])
def get_video(request, video_id):
    video = get_object_or_404(ProcessedVideo, pk=str(video_id))

    if not video.video_file:
        raise JsonResponse({"message": "Video not found"}, status=404)

    video_path = video.video_file.path

    response = FileResponse(open(video_path, "rb"))
    response["Content-Type"] = "video/mp4"
    response["Content-Length"] = str(video.video_file.size)
    response["Content-Disposition"] = f'inline; filename="{video.video_file.name}"'

    return response


@api_view(["GET"])
def get_image(request, image):
    return FileResponse(
        open(f"media/thumbnails/{image}", "rb"), content_type="image/webp"
    )


@api_view(["GET"])
def get_description(request, video_id):
    video = get_object_or_404(ProcessedVideo, pk=str(video_id))
    if not video.video_description:
        raise JsonResponse({"message: Video description not found"}, status=404)

    return JsonResponse({"videoDescription": video.video_description}, status=200)


@api_view(["GET"])
def get_search_options(request):
    query = request.GET.get("query", "")
    page = int(request.GET.get("page", 0))
    searchPage = bool(int(request.GET.get("searchPage", 0)))

    start = (page) * LOAD_VIDEOS_PER_PAGE
    end = start + LOAD_VIDEOS_PER_PAGE

    suggestions = ProcessedVideo.objects.filter(video_title__icontains=query)[start:end]
    if searchPage:
        return Response([s.pk for s in suggestions])

    return Response(video.video_title for video in suggestions)


@api_view(["POST"])
def subscribe(request):
    id_token = request.headers.get("Authorization")
    auth.verify_id_token(id_token)

    data = None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON format"}, status=400
        )

    user_id = data["userId"]
    channel_id = data["channelId"]

    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    channel_ref = db.collection("users").document(channel_id)
    channeld_doc = channel_ref.get()

    batch = db.batch()

    if user_doc.exists and channeld_doc.exists:
        user_data = user_doc.to_dict()
        if channel_id in user_data["subscribed_to"]:
            del user_data["subscribed_to"][channel_id]
            batch.update(user_ref, {"subscribed_to": user_data["subscribed_to"]})
            batch.update(channel_ref, {"subscriber_count": firestore.Increment(-1)})
        else:
            user_data["subscribed_to"][channel_id] = True
            batch.update(user_ref, {"subscribed_to": user_data["subscribed_to"]})
            batch.update(channel_ref, {"subscriber_count": firestore.Increment(1)})

    batch.commit()
    return HttpResponse({"message": "(Un)Subscribed"}, status=200)


@api_view(["POST"])
def like(request):
    id_token = request.headers.get("Authorization")
    auth.verify_id_token(id_token)

    data = None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON format"}, status=400
        )

    user_id = data["userId"]
    video_id = data["videoId"]
    has_liked = data["hasLiked"]  # has pressed the like button

    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    video_ref = db.collection("videos").document(video_id)
    video_doc = video_ref.get()

    batch = db.batch()

    def increment_del(batch, field1, field2, video_data, val=-1) -> None:
        del video_data[field1][user_id]
        batch.update(
            video_ref, {field1: video_data[field1], field2: firestore.Increment(val)}
        )

    def increment_add(batch, field1, field2, video_data, val=1) -> None:
        video_data[field1][user_id] = True
        batch.update(
            video_ref, {field1: video_data[field1], field2: firestore.Increment(val)}
        )

    if user_doc.exists and video_doc.exists:
        video_data = video_doc.to_dict()
        if has_liked:
            if user_id in video_data["dislikedBy"]:
                increment_del(batch, "dislikedBy", "dislikes", video_data)
            if user_id in video_data["likedBy"]:
                increment_del(batch, "likedBy", "likes", video_data)
            else:
                increment_add(batch, "likedBy", "likes", video_data)

        else:
            if user_id in video_data["likedBy"]:
                increment_del(batch, "likedBy", "likes", video_data)

            if user_id in video_data["dislikedBy"]:
                increment_del(batch, "dislikedBy", "dislikes", video_data)
            else:
                increment_add(batch, "dislikedBy", "dislikes", video_data)

    batch.commit()
    return HttpResponse({"message": "(Dis)Liked"}, status=200)


@api_view(["PUT"])
def get_like_info(request):
    data = None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON format"}, status=400
        )

    user_id = data["userId"]
    video_id = data["videoId"]

    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    video_ref = db.collection("videos").document(video_id)
    video_doc = video_ref.get()

    if user_doc.exists and video_doc.exists:
        video_data = video_doc.to_dict()
        return Response(
            {
                "liked": user_id in video_data["likedBy"],
                "disliked": user_id in video_data["dislikedBy"],
            }
        )
    return JsonResponse({"message": "Failed to fetch"}, status=400)


@api_view(["POST"])
def like_comment(request):
    id_token = request.headers.get("Authorization")
    auth.verify_id_token(id_token)

    data = None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON format"}, status=400
        )

    user_id = data["userId"]
    comment_id = data["commentId"]

    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    comment_ref = db.collection("comments").document(comment_id)
    comment_doc = comment_ref.get()

    batch = db.batch()

    def increment_del(batch, field1, field2, comment_data, val=-1) -> None:
        del comment_data[field1][user_id]
        batch.update(
            comment_ref,
            {field1: comment_data[field1], field2: firestore.Increment(val)},
        )

    def increment_add(batch, field1, field2, comment_data, val=1) -> None:
        comment_data[field1][user_id] = True
        batch.update(
            comment_ref,
            {field1: comment_data[field1], field2: firestore.Increment(val)},
        )

    if user_doc.exists and comment_doc.exists:
        comment_data = comment_doc.to_dict()
        if user_id in comment_data["likedBy"]:
            increment_del(batch, "likedBy", "likes", comment_data)
        else:
            increment_add(batch, "likedBy", "likes", comment_data)

    batch.commit()
    return HttpResponse({"message": "(Dis)Liked"}, status=200)


@api_view(["POST"])
def subscriptions(request):
    id_token = request.headers.get("Authorization")
    auth.verify_id_token(id_token)

    data = None
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON format"}, status=400
        )

    weeksAgo = data["weeksAgo"]
    subscriptions = data["subscriptions"]

    cutoff = datetime.now() - timedelta(weeks=2*weeksAgo)
    new_subscriptions = [[] for _ in range(len(subscriptions))]
    res = []
    max_iter = 30

    for i, (channel_id, last_video) in enumerate(subscriptions):
        channel_ref = db.collection("users").document(channel_id)
        channel_doc = channel_ref.get()
        if channel_doc.exists:
            channel_data = channel_doc.to_dict()
            video_ids = channel_data["video_ids"][::-1]

            l, r = last_video, len(video_ids) - 1
            while l <= r and max_iter:
                m = (l + r) // 2
                video_doc = db.collection("videos").document(video_ids[m]).get()
                max_iter -= 1
                if video_doc.exists:
                    video_data = video_doc.to_dict()
                    timestamp = timezone.make_naive(video_data["timestamp"])
                    if timestamp > cutoff:
                        l = m + 1
                    else:
                        r = m - 1

            new_end = min(l, r) + 1
            for video_id in video_ids[last_video:new_end]:
                video_doc = db.collection("videos").document(video_id).get()
                if video_doc.exists:
                    video_data = video_doc.to_dict()
                    res.append(
                        [
                            video_id,
                            timezone.make_naive(video_data["timestamp"]).timestamp(),
                        ]
                    )

            new_subscriptions[i] = [channel_id, new_end]

    res = sorted(res, key=lambda x: x[1], reverse=True)
    return Response(
        {
            "items": [video_id for video_id, _ in res],
            "subscriptions": new_subscriptions,
        },
        status=200,
    )
