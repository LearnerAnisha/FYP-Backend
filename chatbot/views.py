from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import uuid
from rest_framework.permissions import AllowAny
from .models import ChatConversation, ChatMessage, CropSuggestion
from .serializers import (
    WeatherRequestSerializer,
    CropSuggestionRequestSerializer,
    CropSuggestionSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    ChatConversationSerializer
)
from .weather_service import WeatherService
from .gemini_service import GeminiService


class WeatherView(APIView):
    """
    GET endpoint to fetch weather data
    Usage: GET /api/weather/?location=Kathmandu
    """
    
    def get(self, request):
        # Validate input
        serializer = WeatherRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        location = serializer.validated_data['location']
        
        try:
            # Get weather data
            weather_service = WeatherService()
            weather_data = weather_service.get_weather_data(location)
            
            return Response({
                'success': True,
                'location': location,
                'current_weather': weather_data['current'],
                'forecast': weather_data['forecast']
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CropSuggestionView(APIView):
    """
    POST endpoint to get AI-generated crop suggestions
    This is your main feature!
    
    Usage: POST /api/crop-suggestion/
    Body: {
        "location": "Kathmandu",
        "crop_name": "Rice",
        "growth_stage": "Flowering",
        "session_id": "optional-session-id"
    }
    """
    
    def post(self, request):
        # Validate input
        serializer = CropSuggestionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        location = serializer.validated_data['location']
        crop_name = serializer.validated_data['crop_name']
        growth_stage = serializer.validated_data['growth_stage']
        session_id = serializer.validated_data.get('session_id', str(uuid.uuid4()))
        
        try:
            # Step 1: Get weather data
            weather_service = WeatherService()
            weather_data = weather_service.get_weather_data(location)
            
            # Step 2: Get AI suggestion using Gemini
            gemini_service = GeminiService()
            suggestion = gemini_service.get_crop_suggestion(
                crop_name=crop_name,
                growth_stage=growth_stage,
                weather_data=weather_data
            )
            
            # Step 3: Get or create conversation
            conversation, created = ChatConversation.objects.get_or_create(
            session_id=session_id,
            user = request.user
           )

            # Step 4: Save to database
            crop_suggestion = CropSuggestion.objects.create(
                conversation=conversation,
                crop_name=crop_name,
                growth_stage=growth_stage,
                weather_conditions=weather_data,
                suggestion=suggestion
            )
            
            # Step 5: Return response
            return Response({
                'success': True,
                'session_id': session_id,
                'crop_name': crop_name,
                'growth_stage': growth_stage,
                'weather': weather_data,
                'suggestion': suggestion,
                'created_at': crop_suggestion.created_at
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatView(APIView):
    """
    POST endpoint for general chatbot conversation
    
    Usage: POST /api/chat/
    Body: {
        "session_id": "unique-session-id",
        "message": "What fertilizer should I use for tomatoes?"
    }
    """
    
    def post(self, request):
        # Validate input
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        session_id = serializer.validated_data['session_id']
        user_message = serializer.validated_data['message']
        
        try:
            # Get or create conversation
            conversation, created = ChatConversation.objects.get_or_create(
                session_id=session_id,
                user = request.user
            )          
            
            # Save user message
            ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=user_message
            )
            
            # Get conversation history for Gemini (last 10 messages)
            messages = ChatMessage.objects.filter(
                conversation=conversation
            ).order_by('-timestamp')[:10]
            
            # Convert to Gemini format
            conversation_history = []
            for msg in reversed(messages[1:]):  # Exclude current user message
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Get AI response using Gemini
            gemini_service = GeminiService()
            ai_response = gemini_service.chat_with_context(
                user_message, 
                conversation_history
            )
            
            # Save AI response
            assistant_message = ChatMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response
            )
            
            return Response({
                'success': True,
                'session_id': session_id,
                'response': ai_response,
                'timestamp': assistant_message.timestamp
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationHistoryView(APIView):
    permission_classes = [AllowAny]
    """
    GET endpoint to retrieve conversation history
    Usage: GET /api/conversation/{session_id}/
    """
    
    def get(self, request, session_id):
        try:
            conversation = ChatConversation.objects.get(session_id=session_id)
            serializer = ChatConversationSerializer(conversation)
            return Response({
                'success': True,
                'conversation': serializer.data
            }, status=status.HTTP_200_OK)
        
        except ChatConversation.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)