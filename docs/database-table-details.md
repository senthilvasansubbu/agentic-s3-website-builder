# Database Table Details

Below are the details for all tables defined in the database schema. Each table lists its columns, types, and a brief description.

---

## users
| Column              | Type           | Description                                 |
|---------------------|----------------|---------------------------------------------|
| user_id             | VARCHAR(36) PK | Primary key, unique user ID                 |
| email               | VARCHAR(320)   | Unique user email                           |
| mobile              | VARCHAR(20)    | User mobile number                          |
| password_hash       | VARCHAR(256)   | Hashed password                             |
| full_name           | VARCHAR(200)   | User's full name                            |
| is_verified         | BOOLEAN        | Email/phone verified                        |
| plan                | VARCHAR(20)    | free | pro | enterprise                      |
| stripe_customer_id  | VARCHAR(64)    | Stripe customer ID                          |
| created_at          | TIMESTAMP_NTZ  | Account creation timestamp                  |
| updated_at          | TIMESTAMP_NTZ  | Last update timestamp                       |

---

## otp_tokens
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| token_id    | VARCHAR(36) PK | Primary key                                 |
| user_id     | VARCHAR(36) FK | References users(user_id)                   |
| otp_code    | VARCHAR(10)    | OTP code                                    |
| channel     | VARCHAR(10)    | email | sms                                  |
| expires_at  | TIMESTAMP_NTZ  | Expiry timestamp                            |
| used        | BOOLEAN        | Whether OTP is used                         |
| created_at  | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## websites
| Column                | Type           | Description                                 |
|-----------------------|----------------|---------------------------------------------|
| website_id            | VARCHAR(36) PK | Primary key                                 |
| user_id               | VARCHAR(36) FK | References users(user_id)                   |
| name                  | VARCHAR(200)   | Website name                                |
| title                 | VARCHAR(300)   | Website title                               |
| description           | VARCHAR(2000)  | Website description                         |
| logo_url              | VARCHAR(500)   | Logo image URL                              |
| domain                | VARCHAR(300)   | Custom domain                               |
| hosting_env           | VARCHAR(20)    | s3 | custom                                  |
| theme                 | VARCHAR(50)    | Theme name                                  |
| custom_css            | TEXT           | Custom CSS                                  |
| pages_json            | VARIANT        | JSON array of page configs                  |
| s3_bucket             | VARCHAR(200)   | S3 bucket name                              |
| image_storage_backend | VARCHAR(20)    | auto | local | s3 | gdrive                   |
| image_storage_config  | VARIANT        | Image storage config                        |
| classification        | VARCHAR(50)    | Website classification                      |
| build_mode            | VARCHAR(20)    | combined | agentic_only                       |
| output_target         | VARCHAR(30)    | legacy | react | vue | php | ...               |
| classification_label  | VARCHAR(120)   | Classification label                        |
| classification_group  | VARCHAR(120)   | Classification group                        |
| input_snapshot_json   | VARIANT        | Input snapshot                              |
| source_context_json   | VARIANT        | Source context                              |
| s3_url                | VARCHAR(500)   | S3 URL                                      |
| status                | VARCHAR(20)    | Website status                              |
| plan_required         | VARCHAR(20)    | free | pro | enterprise                      |
| created_at            | TIMESTAMP_NTZ  | Creation timestamp                          |
| updated_at            | TIMESTAMP_NTZ  | Last update timestamp                       |

---

## cart_categories
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| category_id | VARCHAR(36) PK | Primary key                                 |
| website_id  | VARCHAR(36) FK | References websites(website_id)             |
| parent_id   | VARCHAR(36)    | Parent category ID                          |
| name        | VARCHAR(200)   | Category name                               |
| slug        | VARCHAR(200)   | URL slug                                    |
| description | VARCHAR(1000)  | Category description                        |
| image_url   | VARCHAR(500)   | Image URL                                   |
| sort_order  | INTEGER        | Sort order                                  |
| created_at  | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## cart_items
| Column           | Type           | Description                                 |
|------------------|----------------|---------------------------------------------|
| product_id       | VARCHAR(36) PK | Primary key                                 |
| website_id       | VARCHAR(36) FK | References websites(website_id)             |
| category_id      | VARCHAR(36) FK | References cart_categories(category_id)     |
| name             | VARCHAR(300)   | Product name                                |
| slug             | VARCHAR(300)   | URL slug                                    |
| description      | TEXT           | Product description                         |
| price            | NUMBER(12,2)   | Product price                               |
| compare_price    | NUMBER(12,2)   | Compare price                               |
| discount_pct     | NUMBER(5,2)    | Discount percent                            |
| currency         | VARCHAR(3)     | Currency code                               |
| stock_quantity   | INTEGER        | Stock quantity                              |
| image_url        | VARCHAR(500)   | Main image URL                              |
| images_json      | VARIANT        | JSON array of images                        |
| attributes       | VARIANT        | Product attributes                          |
| is_flash_offer   | BOOLEAN        | Flash offer flag                            |
| flash_offer_ends | TIMESTAMP_NTZ  | Flash offer end time                        |
| is_active        | BOOLEAN        | Is product active                           |
| created_at       | TIMESTAMP_NTZ  | Creation timestamp                          |
| updated_at       | TIMESTAMP_NTZ  | Last update timestamp                       |

---

## carts
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| cart_id     | VARCHAR(36) PK | Primary key                                 |
| user_id     | VARCHAR(36) FK | References users(user_id)                   |
| website_id  | VARCHAR(36) FK | References websites(website_id)             |
| session_id  | VARCHAR(100)   | Session identifier                          |
| items_json  | VARIANT        | JSON array of cart items                    |
| currency    | VARCHAR(3)     | Currency code                               |
| created_at  | TIMESTAMP_NTZ  | Creation timestamp                          |
| updated_at  | TIMESTAMP_NTZ  | Last update timestamp                       |

---

## orders
| Column             | Type           | Description                                 |
|--------------------|----------------|---------------------------------------------|
| order_id           | VARCHAR(36) PK | Primary key                                 |
| cart_id            | VARCHAR(36) FK | References carts(cart_id)                   |
| user_id            | VARCHAR(36) FK | References users(user_id)                   |
| website_id         | VARCHAR(36) FK | References websites(website_id)             |
| status             | VARCHAR(20)    | Order status                                |
| total_amount       | NUMBER(12,2)   | Total order amount                          |
| currency           | VARCHAR(3)     | Currency code                               |
| stripe_payment_id  | VARCHAR(120)   | Stripe payment ID                           |
| shipping_address   | VARIANT        | Shipping address (JSON)                     |
| items_snapshot     | VARIANT        | Snapshot of items (JSON)                    |
| created_at         | TIMESTAMP_NTZ  | Creation timestamp                          |
| updated_at         | TIMESTAMP_NTZ  | Last update timestamp                       |

---

## subscriptions
| Column              | Type           | Description                                 |
|---------------------|----------------|---------------------------------------------|
| sub_id              | VARCHAR(36) PK | Primary key                                 |
| user_id             | VARCHAR(36) FK | References users(user_id)                   |
| plan                | VARCHAR(20)    | Plan name                                   |
| stripe_sub_id       | VARCHAR(120)   | Stripe subscription ID                      |
| status              | VARCHAR(20)    | Subscription status                         |
| current_period_end  | TIMESTAMP_NTZ  | Current period end                          |
| next_billing_date   | TEXT           | Next billing date                           |
| created_at          | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## activity_log
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| log_id      | VARCHAR(36) PK | Primary key                                 |
| user_id     | VARCHAR(36) FK | References users(user_id)                   |
| website_id  | VARCHAR(36) FK | References websites(website_id)             |
| event       | VARCHAR(100)   | Event type                                  |
| meta        | VARIANT        | Event metadata                              |
| ip_address  | VARCHAR(45)    | IP address                                  |
| country     | VARCHAR(60)    | Country                                     |
| created_at  | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## payment_configs
| Column              | Type           | Description                                 |
|---------------------|----------------|---------------------------------------------|
| config_id           | VARCHAR(36) PK | Primary key                                 |
| website_id          | VARCHAR(36) FK | References websites(website_id)             |
| gateway             | VARCHAR(30)    | Payment gateway (e.g., stripe)              |
| publishable_key     | VARCHAR(200)   | Publishable key                             |
| secret_key_enc      | VARCHAR(500)   | Encrypted secret key                        |
| webhook_secret_enc  | VARCHAR(500)   | Encrypted webhook secret                    |
| enabled_methods     | VARIANT        | Enabled payment methods                     |
| created_at          | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## feedback
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| feedback_id | VARCHAR(36) PK | Primary key                                 |
| website_id  | VARCHAR(36) FK | References websites(website_id)             |
| name        | VARCHAR(120)   | Name of feedback provider                   |
| email       | VARCHAR(200)   | Email address                               |
| rating      | INTEGER        | Rating (1-5)                                |
| message     | TEXT           | Feedback message                            |
| created_at  | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## monitor_checks
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| check_id    | VARCHAR(36) PK | Primary key                                 |
| website_id  | VARCHAR(36) FK | References websites(website_id)             |
| check_type  | VARCHAR(60)    | Type of check                               |
| status      | VARCHAR(20)    | Check status                                |
| latency_ms  | INTEGER        | Latency in ms                               |
| detail      | TEXT           | Check details                               |
| checked_at  | TIMESTAMP_NTZ  | Check timestamp                             |

---

## monitor_incidents
| Column         | Type           | Description                                 |
|----------------|----------------|---------------------------------------------|
| incident_id    | VARCHAR(36) PK | Primary key                                 |
| website_id     | VARCHAR(36) FK | References websites(website_id)             |
| check_type     | VARCHAR(60)    | Type of check                               |
| severity       | VARCHAR(20)    | Severity                                    |
| status         | VARCHAR(20)    | Incident status                             |
| detail         | TEXT           | Incident details                            |
| notified_at    | TIMESTAMP_NTZ  | Notification timestamp                      |
| resolved_at    | TIMESTAMP_NTZ  | Resolution timestamp                        |
| created_at     | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## payment_reminders
| Column         | Type           | Description                                 |
|----------------|----------------|---------------------------------------------|
| reminder_id    | VARCHAR(36) PK | Primary key                                 |
| user_id        | VARCHAR(36) FK | References users(user_id)                   |
| reminder_type  | VARCHAR(40)    | Type of reminder                            |
| channel        | VARCHAR(20)    | Notification channel                        |
| status         | VARCHAR(20)    | Reminder status                             |
| due_date       | TEXT           | Due date                                    |
| amount         | REAL           | Amount due                                  |
| sent_at        | TIMESTAMP_NTZ  | Sent timestamp                              |

---

## notification_log
| Column        | Type           | Description                                 |
|---------------|----------------|---------------------------------------------|
| log_id        | VARCHAR(36) PK | Primary key                                 |
| user_id       | VARCHAR(36) FK | References users(user_id)                   |
| channel       | VARCHAR(20)    | Notification channel                        |
| destination   | VARCHAR(200)   | Destination address                         |
| subject       | VARCHAR(300)   | Notification subject                        |
| body          | TEXT           | Notification body                           |
| status        | VARCHAR(20)    | Notification status                         |
| error         | TEXT           | Error message                               |
| sent_at       | TIMESTAMP_NTZ  | Sent timestamp                              |

---

## coupons
| Column         | Type           | Description                                 |
|----------------|----------------|---------------------------------------------|
| coupon_id      | VARCHAR(36) PK | Primary key                                 |
| website_id     | VARCHAR(36) FK | References websites(website_id)             |
| code           | VARCHAR(50)    | Coupon code                                 |
| discount_type  | VARCHAR(10)    | percent | fixed                              |
| discount_value | NUMBER(10,2)   | Discount value                              |
| min_order      | NUMBER(10,2)   | Minimum order value                         |
| max_uses       | INTEGER        | Maximum uses                                |
| uses_count     | INTEGER        | Number of times used                        |
| valid_from     | TEXT           | Valid from date                             |
| valid_until    | TEXT           | Valid until date                            |
| is_active      | INTEGER        | Is coupon active                            |
| created_at     | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## advertisements
| Column      | Type           | Description                                 |
|-------------|----------------|---------------------------------------------|
| ad_id       | VARCHAR(36) PK | Primary key                                 |
| website_id  | VARCHAR(36) FK | References websites(website_id)             |
| title       | VARCHAR(200)   | Advertisement title                         |
| image_url   | VARCHAR(500)   | Image URL                                   |
| link_url    | VARCHAR(500)   | Link URL                                    |
| position    | VARCHAR(30)    | Position (e.g., banner)                     |
| is_active   | INTEGER        | Is advertisement active                     |
| starts_at   | TEXT           | Start date                                  |
| ends_at     | TEXT           | End date                                    |
| created_at  | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## notification_campaigns
| Column        | Type           | Description                                 |
|---------------|----------------|---------------------------------------------|
| campaign_id   | VARCHAR(36) PK | Primary key                                 |
| website_id    | VARCHAR(36) FK | References websites(website_id)             |
| owner_id      | VARCHAR(36) FK | References users(user_id)                   |
| title         | VARCHAR(200)   | Campaign title                              |
| channel       | VARCHAR(20)    | Notification channel                        |
| subject       | VARCHAR(300)   | Campaign subject                            |
| body          | TEXT           | Campaign body                               |
| status        | VARCHAR(20)    | Campaign status                             |
| sent_count    | INTEGER        | Number of notifications sent                |
| scheduled_at  | TEXT           | Scheduled date                              |
| sent_at       | TEXT           | Sent date                                   |
| created_at    | TIMESTAMP_NTZ  | Creation timestamp                          |

---

## plan_features
| Column   | Type        | Description                                 |
|----------|-------------|---------------------------------------------|
| plan     | TEXT  PK    | Plan name                                   |
| feature  | TEXT  PK    | Feature name                                |
| enabled  | INTEGER     | Is feature enabled (0/1)                    |

---
