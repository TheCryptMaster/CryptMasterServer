--
-- PostgreSQL database dump
--

-- Dumped from database version 16.1
-- Dumped by pg_dump version 16.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_servers; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.app_servers (
    id integer NOT NULL,
    server_name character varying NOT NULL,
    ip_address character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.app_servers OWNER TO cryptmaster;

--
-- Name: app_servers_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.app_servers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.app_servers_id_seq OWNER TO cryptmaster;

--
-- Name: app_servers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.app_servers_id_seq OWNED BY public.app_servers.id;


--
-- Name: cm_control; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.cm_control (
    id integer NOT NULL,
    install_date timestamp with time zone DEFAULT now() NOT NULL,
    version_active character varying NOT NULL,
    previous_version character varying DEFAULT 'none'::character varying NOT NULL
);


ALTER TABLE public.cm_control OWNER TO cryptmaster;

--
-- Name: cm_control_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.cm_control_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cm_control_id_seq OWNER TO cryptmaster;

--
-- Name: cm_control_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.cm_control_id_seq OWNED BY public.cm_control.id;


--
-- Name: cm_status; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.cm_status (
    id integer NOT NULL,
    system_active boolean DEFAULT true NOT NULL,
    disabled_until timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cm_status OWNER TO cryptmaster;

--
-- Name: cm_status_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.cm_status_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cm_status_id_seq OWNER TO cryptmaster;

--
-- Name: cm_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.cm_status_id_seq OWNED BY public.cm_status.id;


--
-- Name: event_log; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.event_log (
    id integer NOT NULL,
    event_type character varying NOT NULL,
    significant boolean DEFAULT false NOT NULL,
    details character varying NOT NULL
);


ALTER TABLE public.event_log OWNER TO cryptmaster;

--
-- Name: event_log_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.event_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.event_log_id_seq OWNER TO cryptmaster;

--
-- Name: event_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.event_log_id_seq OWNED BY public.event_log.id;


--
-- Name: secrets; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.secrets (
    id integer NOT NULL,
    secret_name character varying NOT NULL,
    secret_pass character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.secrets OWNER TO cryptmaster;

--
-- Name: secrets_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.secrets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.secrets_id_seq OWNER TO cryptmaster;

--
-- Name: secrets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.secrets_id_seq OWNED BY public.secrets.id;


--
-- Name: server_secret_allow; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.server_secret_allow (
    id integer NOT NULL,
    server integer NOT NULL,
    secret integer NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.server_secret_allow OWNER TO cryptmaster;

--
-- Name: server_secret_allow_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.server_secret_allow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.server_secret_allow_id_seq OWNER TO cryptmaster;

--
-- Name: server_secret_allow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.server_secret_allow_id_seq OWNED BY public.server_secret_allow.id;


--
-- Name: user_accounts; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.user_accounts (
    id integer NOT NULL,
    username character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    user_otp_hash character varying NOT NULL,
    active_until timestamp with time zone DEFAULT (now() + '365 days'::interval) NOT NULL
);


ALTER TABLE public.user_accounts OWNER TO cryptmaster;

--
-- Name: user_accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.user_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_accounts_id_seq OWNER TO cryptmaster;

--
-- Name: user_accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.user_accounts_id_seq OWNED BY public.user_accounts.id;


--
-- Name: app_servers id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.app_servers ALTER COLUMN id SET DEFAULT nextval('public.app_servers_id_seq'::regclass);


--
-- Name: cm_control id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.cm_control ALTER COLUMN id SET DEFAULT nextval('public.cm_control_id_seq'::regclass);


--
-- Name: cm_status id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.cm_status ALTER COLUMN id SET DEFAULT nextval('public.cm_status_id_seq'::regclass);


--
-- Name: event_log id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.event_log ALTER COLUMN id SET DEFAULT nextval('public.event_log_id_seq'::regclass);


--
-- Name: secrets id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.secrets ALTER COLUMN id SET DEFAULT nextval('public.secrets_id_seq'::regclass);


--
-- Name: server_secret_allow id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.server_secret_allow ALTER COLUMN id SET DEFAULT nextval('public.server_secret_allow_id_seq'::regclass);


--
-- Name: user_accounts id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.user_accounts ALTER COLUMN id SET DEFAULT nextval('public.user_accounts_id_seq'::regclass);


--
-- Name: app_servers app_servers_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.app_servers
    ADD CONSTRAINT app_servers_pkey PRIMARY KEY (id);


--
-- Name: app_servers app_servers_unique; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.app_servers
    ADD CONSTRAINT app_servers_unique UNIQUE (ip_address);


--
-- Name: app_servers app_servers_unique_1; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.app_servers
    ADD CONSTRAINT app_servers_unique_1 UNIQUE (server_name);


--
-- Name: cm_control cm_control_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.cm_control
    ADD CONSTRAINT cm_control_pkey PRIMARY KEY (id);


--
-- Name: cm_status cm_status_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.cm_status
    ADD CONSTRAINT cm_status_pkey PRIMARY KEY (id);


--
-- Name: event_log event_log_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.event_log
    ADD CONSTRAINT event_log_pkey PRIMARY KEY (id);


--
-- Name: secrets secrets_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.secrets
    ADD CONSTRAINT secrets_pkey PRIMARY KEY (id);


--
-- Name: server_secret_allow server_secret_allow_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.server_secret_allow
    ADD CONSTRAINT server_secret_allow_pkey PRIMARY KEY (id);


--
-- Name: user_accounts user_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.user_accounts
    ADD CONSTRAINT user_accounts_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--