// Espera a que el documento HTML esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Selecciona todos los elementos con la clase 'category'
    var categories = document.querySelectorAll('.category');

    // Define un array de colores para las luces LED
    var colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', '#FF00FF'];

    // Función para obtener un color aleatorio del array de colores
    function getRandomColor() {
        return colors[Math.floor(Math.random() * colors.length)];
    }

    // Agrega un event listener para el evento 'click' en cada categoría
    categories.forEach(function(category) {
        category.addEventListener('click', function() {
            // Obtiene un color aleatorio del array de colores
            var randomColor = getRandomColor();

            // Aplica el color aleatorio como fondo de la categoría
            category.style.backgroundColor = randomColor;

            // Después de 0.5 segundos, restaura el color original de fondo
            setTimeout(function() {
                category.style.backgroundColor = '';
            }, 500);
        });
    });
});
