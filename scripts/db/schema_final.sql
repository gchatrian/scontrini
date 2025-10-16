-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.household_members (
  household_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role text NOT NULL CHECK (role = ANY (ARRAY['owner'::text, 'member'::text])),
  joined_at timestamp with time zone DEFAULT now(),
  CONSTRAINT household_members_pkey PRIMARY KEY (household_id, user_id),
  CONSTRAINT household_members_household_id_fkey FOREIGN KEY (household_id) REFERENCES public.households(id),
  CONSTRAINT household_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.households (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT households_pkey PRIMARY KEY (id)
);
CREATE TABLE public.normalized_products (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL UNIQUE,
  brand text,
  category text,
  subcategory text,
  size text,
  unit_type text,
  barcode text,
  tags ARRAY,
  nutritional_info jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  verification_status text DEFAULT 'auto_verified'::text CHECK (verification_status = ANY (ARRAY['auto_verified'::text, 'pending_review'::text, 'user_verified'::text, 'rejected'::text])),
  CONSTRAINT normalized_products_pkey PRIMARY KEY (id)
);
CREATE TABLE public.product_mappings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  raw_name text NOT NULL,
  normalized_product_id uuid NOT NULL,
  store_name text,
  confidence_score double precision CHECK (confidence_score >= 0::double precision AND confidence_score <= 1::double precision),
  verified_by_user boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  requires_manual_review boolean DEFAULT false,
  interpretation_details jsonb DEFAULT '{}'::jsonb,
  reviewed_at timestamp with time zone,
  reviewed_by uuid,
  CONSTRAINT product_mappings_pkey PRIMARY KEY (id),
  CONSTRAINT product_mappings_normalized_product_id_fkey FOREIGN KEY (normalized_product_id) REFERENCES public.normalized_products(id),
  CONSTRAINT product_mappings_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES auth.users(id)
);
CREATE TABLE public.purchase_history (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  household_id uuid NOT NULL,
  receipt_id uuid NOT NULL,
  receipt_item_id uuid NOT NULL,
  normalized_product_id uuid,
  purchase_date date NOT NULL,
  store_name text,
  quantity numeric,
  unit_price numeric,
  total_price numeric NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  store_id uuid,
  CONSTRAINT purchase_history_pkey PRIMARY KEY (id),
  CONSTRAINT purchase_history_household_id_fkey FOREIGN KEY (household_id) REFERENCES public.households(id),
  CONSTRAINT purchase_history_receipt_id_fkey FOREIGN KEY (receipt_id) REFERENCES public.receipts(id),
  CONSTRAINT purchase_history_receipt_item_id_fkey FOREIGN KEY (receipt_item_id) REFERENCES public.receipt_items(id),
  CONSTRAINT purchase_history_normalized_product_id_fkey FOREIGN KEY (normalized_product_id) REFERENCES public.normalized_products(id),
  CONSTRAINT purchase_history_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id)
);
CREATE TABLE public.receipt_items (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  receipt_id uuid NOT NULL,
  raw_product_name text NOT NULL,
  quantity numeric DEFAULT 1,
  unit_price numeric,
  total_price numeric NOT NULL,
  line_number integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT receipt_items_pkey PRIMARY KEY (id),
  CONSTRAINT receipt_items_receipt_id_fkey FOREIGN KEY (receipt_id) REFERENCES public.receipts(id)
);
CREATE TABLE public.receipts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  household_id uuid NOT NULL,
  uploaded_by uuid,
  image_url text NOT NULL,
  store_name text,
  store_address text,
  receipt_date date,
  receipt_time time without time zone,
  total_amount numeric,
  payment_method text,
  discount_amount numeric,
  raw_ocr_text text,
  ocr_confidence double precision CHECK (ocr_confidence >= 0::double precision AND ocr_confidence <= 1::double precision),
  processing_status text DEFAULT 'pending'::text CHECK (processing_status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text])),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  store_id uuid,
  CONSTRAINT receipts_pkey PRIMARY KEY (id),
  CONSTRAINT receipts_household_id_fkey FOREIGN KEY (household_id) REFERENCES public.households(id),
  CONSTRAINT receipts_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES auth.users(id),
  CONSTRAINT receipts_store_id_fkey FOREIGN KEY (store_id) REFERENCES public.stores(id)
);
CREATE TABLE public.stores (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  chain text,
  branch_name text,
  vat_number text,
  company_name text,
  address_full text,
  address_street text,
  address_city text,
  address_province text,
  address_postal_code text,
  address_country text DEFAULT 'IT'::text,
  latitude numeric,
  longitude numeric,
  store_type text,
  is_mock boolean DEFAULT false,
  data_quality_score double precision CHECK (data_quality_score >= 0::double precision AND data_quality_score <= 1::double precision),
  phone text,
  email text,
  website text,
  opening_hours jsonb,
  total_receipts integer DEFAULT 0,
  avg_receipt_amount numeric,
  last_receipt_date date,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT stores_pkey PRIMARY KEY (id)
);