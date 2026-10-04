# PJzen Universal Docker Image
FROM php:8.2-apache

# Habilitar mod_rewrite do Apache
RUN a2enmod rewrite

# Copiar arquivos do projeto
WORKDIR /var/www/html
COPY . /var/www/html/

# Permissões da pasta de uploads e banco SQLite
RUN mkdir -p /var/www/html/uploads && \
    chown -R www-data:www-data /var/www/html && \
    chmod -R 775 /var/www/html/uploads

EXPOSE 80
CMD ["apache2-foreground"]
