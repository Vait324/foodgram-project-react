from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from .models import (Favorites, Follow, Ingredient, IngredientInRecipe,
                     Purchase, Recipe, Tag, User)


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=request.user, author=obj.id).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('__all__')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'amount', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredients_amounts',
        many=True, read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'name', 'text',
                  'image', 'ingredients', 'cooking_time',
                  'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Favorites.objects.filter(user=request.user,
                                        recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Purchase.objects.filter(user=request.user,
                                       recipe=obj).exists()

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        ingredients_set = set()
        if ingredients is None:
            raise serializers.ValidationError(
                    'Добавьте минимум один ингредиент.'
                )
        for ingredient in ingredients:
            if int(ingredient.get('amount')) <= 0:
                raise serializers.ValidationError(
                    'Кол-во ингредиента должно быть больше 0.'
                )
            id = ingredient.get('id')
            if id in ingredients_set:
                raise serializers.ValidationError(
                    'Ингредиент в рецепте не должен повторяться.'
                )
            ingredients_set.add(id)
        data['ingredients'] = ingredients

        return data

    def create_or_update_method(self, f_tags, f_ingredients, f_recipe):
        for tag_id in f_tags:
            f_recipe.tags.add(get_object_or_404(Tag, pk=tag_id))
        for ingredient in f_ingredients:
            IngredientInRecipe.objects.create(
                recipe=f_recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount')
            )

    def create(self, validated_data):
        image = validated_data.pop('image')
        recipe = Recipe.objects.create(image=image, **validated_data)
        tags = self.initial_data.get('tags')
        ingredients = validated_data.pop('ingredients')
        self.create_or_update_method(f_tags=tags, f_ingredients=ingredients,
                                     f_recipe=recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        tags = self.initial_data.get('tags')
        ingredients = validated_data.get('ingredients')
        IngredientInRecipe.objects.filter(recipe=instance).delete()
        self.create_or_update_method(f_tags=tags, f_ingredients=ingredients,
                                     f_recipe=instance)
        if validated_data.get('image') is not None:
            instance.image = validated_data.get('image')
        instance.name = validated_data.get('name')
        instance.text = validated_data.get('text')
        instance.cooking_time = validated_data.get('cooking_time')
        instance.save()
        return instance


class FollowerRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowerSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=obj.user, author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.author)
        if limit is not None:
            queryset = Recipe.objects.filter(
                author=obj.author
            )[:int(limit)]

        return FollowerRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        author = obj.author
        return author.recipes.count()


class FollowSerializer(serializers.ModelSerializer):
    queryset = User.objects.all()
    user = serializers.PrimaryKeyRelatedField(queryset=queryset)
    author = serializers.PrimaryKeyRelatedField(queryset=queryset)

    class Meta:
        model = Follow
        fields = ('user', 'author')

    def validate(self, data):
        request = self.context.get('request')
        author_id = data['author'].id
        follow_exists = Follow.objects.filter(
            user=request.user,
            author__id=author_id
        ).exists()

        if request.method == 'GET':
            if request.user.id == author_id:
                raise serializers.ValidationError(
                    'Нельзя подписаться на себя.'
                )
            if follow_exists:
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого пользователя.'
                )

        return data


class FavoritesSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Favorites
        fields = ('user', 'recipe')

    def validate(self, data):
        request = self.context.get('request')
        recipe_id = data['recipe'].id
        favorite_exists = Favorites.objects.filter(
            user=request.user,
            recipe__id=recipe_id
        ).exists()

        if request.method == 'GET' and favorite_exists:
            raise serializers.ValidationError(
                'Рецепт уже в избранном.'
            )

        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return FollowerRecipeSerializer(
            instance.recipe,
            context=context).data


class PurchaseSerializer(FavoritesSerializer):
    class Meta(FavoritesSerializer.Meta):
        model = Purchase

    def validate(self, data):
        request = self.context.get('request')
        recipe_id = data['recipe'].id
        purchase_exists = Purchase.objects.filter(
            user=request.user,
            recipe__id=recipe_id
        ).exists()

        if request.method == 'GET' and purchase_exists:
            raise serializers.ValidationError(
                'Рецепт уже в списке покупок.'
            )

        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return FollowerRecipeSerializer(
            instance.recipe,
            context=context).data
