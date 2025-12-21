-- ===============================
-- 添加 Immich 图片搜索插件
-- ===============================
START TRANSACTION;

-- Immich 图片搜索插件
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_IMMICH_SEARCH',
        'Plugin',
        'search_from_immich',
        'Immich 图片搜索',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'description',
                        'type', 'string',
                        'label', '插件描述（用于提示LLM何时调用）',
                        'default', '当用户想要搜索照片、查看图片、查找特定人物或地点的照片时，调用本方法从 Immich 相册中搜索图片'
                )
        ),
        80, 0, NOW(), 0, NOW())
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    fields = VALUES(fields),
    sort = VALUES(sort),
    updater = 0,
    update_date = NOW();

COMMIT;

