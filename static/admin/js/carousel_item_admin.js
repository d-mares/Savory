(function($) {
    'use strict';
    $(document).ready(function() {
        var $recipeSelect = $('#id_recipe');
        var $imageSelect = $('#id_image');
        var $imagePreview = $('.field-image_preview .readonly');
        
        function updateImagePreview(url) {
            if (url) {
                $imagePreview.html(
                    '<img src="' + url + '" style="max-height: 100px; max-width: 100px;" alt="Preview" />'
                );
            } else {
                $imagePreview.html('No image');
            }
        }

        function updateImageChoices() {
            var recipeId = $recipeSelect.val();

            if (!recipeId) {
                $imageSelect.html('<option value="">---------</option>').prop('disabled', true);
                updateImagePreview(null);
                return;
            }

            $.ajax({
                url: '/recipes/recipe/' + recipeId + '/images/',
                method: 'GET',
                success: function(data) {
                    var options = ['<option value="">---------</option>'];
                    
                    data.forEach(function(image) {
                        options.push(
                            '<option value="' + image.id + '" data-url="' + image.url + '">' +
                            'Image ' + image.order + ' - ' + image.url.split('/').pop() +
                            '</option>'
                        );
                    });
                    
                    $imageSelect
                        .html(options.join(''))
                        .prop('disabled', false);

                    // Restore previous selection if exists
                    var initialImageId = $imageSelect.val();
                    if (initialImageId) {
                        $imageSelect.val(initialImageId);
                    }
                    
                    $imageSelect.trigger('change');
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching images:', error);
                    $imageSelect
                        .html('<option value="">Error loading images</option>')
                        .prop('disabled', true);
                }
            });
        }

        // Update images when recipe changes
        $recipeSelect.on('change', updateImageChoices);

        // Handle image selection change
        $imageSelect.on('change', function() {
            var $selected = $(this).find('option:selected');
            var imageUrl = $selected.data('url');
            updateImagePreview(imageUrl);
        });

        // Initial update if recipe is selected
        if ($recipeSelect.val()) {
            updateImageChoices();
        }
    });
})(django.jQuery); 