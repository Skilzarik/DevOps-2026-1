# Трассировка: требования ТЗ и автоматические тесты

Формат ссылки: `файл.py::имя_теста` (каталог `backend/tests/`).

| ID | Требование ТЗ | Тесты |
|---|---|---|
| R01 | 4.3b. Регистрация пользователя, имя уникально | test_auth_api.py::test_register_creates_user_without_exposing_password, test_auth_api.py::test_register_duplicate_username_rejected |
| R02 | 4.3b. Вход выдаёт JWT, неверные данные отклоняются | test_auth_api.py::test_login_returns_bearer_token, test_auth_api.py::test_login_wrong_password_rejected, test_auth_api.py::test_login_unknown_user_rejected |
| R03 | 6.4. Защищённые маршруты закрыты без токена или с неверным токеном | test_auth_api.py::test_me_requires_token, test_auth_api.py::test_me_rejects_invalid_token, test_auth_api.py::test_token_for_unknown_user_rejected, test_catalog.py::test_musicians_list_requires_token, test_sales.py::test_sale_requires_token |
| R04 | 6.4. JWT: подпись и срок действия проверяются | test_unit_auth_and_schemas.py::test_token_contains_subject_and_expiry, test_unit_auth_and_schemas.py::test_expired_token_is_rejected, test_unit_auth_and_schemas.py::test_token_signed_with_other_key_is_rejected |
| R05 | 2.2. Пароли хранятся только в виде хеша | test_auth_api.py::test_password_is_stored_hashed, test_unit_auth_and_schemas.py::test_password_hash_is_not_plaintext, test_unit_auth_and_schemas.py::test_password_verification |
| R06 | 3.2, 6.4. Продавец не меняет каталог музыкантов | test_catalog.py::test_seller_cannot_create_musician, test_catalog.py::test_seller_cannot_delete_musician |
| R07 | 3.2, 6.4. Продавец не удаляет диски и не меняет цены и остатки | test_catalog.py::test_seller_cannot_create_disc, test_catalog.py::test_seller_cannot_restock, test_catalog.py::test_seller_cannot_delete_disc |
| R08 | 3.2. Администратор управляет каталогом и остатками | test_catalog.py::test_admin_creates_musician, test_catalog.py::test_admin_creates_disc, test_catalog.py::test_restock_increases_stock |
| R09 | 4.2. Диск связан с существующим исполнителем | test_catalog.py::test_disc_with_unknown_musician_rejected |
| R10 | 2.2. Некорректные данные отклоняются (цена, остаток, количество) | test_catalog.py::test_disc_price_must_be_positive_api, test_catalog.py::test_disc_negative_stock_rejected, test_sales.py::test_sale_quantity_must_be_positive, test_unit_auth_and_schemas.py::test_disc_price_must_be_positive |
| R11 | 4.3b, 6.4. Продажа сверх остатка отклоняется, остаток не меняется | test_sales.py::test_sale_exceeding_stock_is_rejected_and_stock_unchanged, test_sales.py::test_sale_of_out_of_stock_disc_rejected |
| R12 | 6.3. После продажи остаток уменьшается, сумма считается верно | test_sales.py::test_sale_decreases_stock_and_records_total, test_sales.py::test_consecutive_sales_accumulate |
| R13 | Граничный случай: можно продать ровно весь остаток | test_sales.py::test_sale_of_entire_stock_is_allowed |
| R14 | 3.2. Продавец оформляет продажу, продавец фиксируется | test_sales.py::test_seller_can_register_sale |
| R15 | 6.4. Нельзя удалить диск, по которому есть продажи | test_catalog.py::test_disc_with_sales_cannot_be_deleted |
| R16 | 6.4. Целостность: нельзя удалить исполнителя, диски которого продавались | test_catalog.py::test_musician_with_sold_discs_cannot_be_deleted |
| R17 | 4.3a. Адрес /health: 200 при рабочей БД, 503 при недоступной | test_service.py::test_health_ok, test_service.py::test_health_reports_503_when_database_is_down |
| R18 | 4.3a. Глобальная обработка некорректных запросов | test_service.py::test_invalid_json_returns_422, test_service.py::test_unknown_route_returns_json_404 |
| R19 | 4.3a. Настройки только через переменные окружения | test_settings.py::test_settings_are_read_from_environment, test_settings.py::test_database_url_is_mandatory, test_settings.py::test_secret_key_has_no_insecure_default |
| R20 | 4.2. Список продаж, новые первыми | test_sales.py::test_sales_list_is_newest_first |
| R21 | 7. Автоматически генерируемая документация API | test_service.py::test_openapi_docs_are_available |
| R22 | 5. Схема БД создаётся миграциями (чистая и заполненная БД) | test_migrations.py::test_clean_db_is_created_by_migrations, test_migrations.py::test_upgrade_keeps_existing_data_and_fixes_invalid_values |
| R23 | 4.3b. Веб-интерфейс: формы, таблицы, кнопки | нет автоматической проверки (ручное тестирование по ТЗ 6.1; тест лишь проверяет отдачу страницы) |
