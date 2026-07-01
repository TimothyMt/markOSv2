-- Migration 012: intake_extra cho intake web đa-level (D-032)
-- Chứa câu hỏi chiến lược tầng CMO không có cột riêng (JTBD, lựa-chọn-thay-thế,
-- khác biệt, objection, giá/AOV) + provenance từng field
-- (typed / suggested / inferred) để output T1-T3 gắn nhãn "(giả định)" đúng chỗ.
ALTER TABLE user_business_profile
    ADD COLUMN IF NOT EXISTS intake_extra JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN user_business_profile.intake_extra IS
    'D-032: {answers:{jtbd,competitive_alternative,differentiation,objection,price_point}, provenance:{field:typed|suggested|inferred}}';
