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
-- Name: cryptmaster_warden; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.cryptmaster_warden (
    id integer NOT NULL,
    system_online boolean DEFAULT true NOT NULL,
    api_open_mins integer DEFAULT 5 NOT NULL,
    api_lock_mins integer DEFAULT 60 NOT NULL,
    api_open boolean DEFAULT false NOT NULL,
    open_until timestamp with time zone DEFAULT now() NOT NULL,
    api_lockdown boolean DEFAULT false NOT NULL,
    lockdown_until timestamp with time zone DEFAULT now() NOT NULL,
    send_alerts boolean DEFAULT false NOT NULL,
    host_name character varying DEFAULT 'secure-api.yourdomain.com'::character varying NOT NULL
);


ALTER TABLE public.cryptmaster_warden OWNER TO cryptmaster;

--
-- Name: cryptmaster_warden_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.cryptmaster_warden_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cryptmaster_warden_id_seq OWNER TO cryptmaster;

--
-- Name: cryptmaster_warden_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.cryptmaster_warden_id_seq OWNED BY public.cryptmaster_warden.id;


--
-- Name: event_log; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.event_log (
    id integer NOT NULL,
    event_type character varying NOT NULL,
    significant boolean DEFAULT false NOT NULL,
    details character varying NOT NULL,
    linked_ipv4_wl integer,
    linked_ipv4_bl integer,
    event_timestamp timestamp with time zone DEFAULT now() NOT NULL
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
-- Name: ipv4_allow; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.ipv4_allow (
    id integer NOT NULL,
    ipv4_address character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    date_added timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.ipv4_allow OWNER TO cryptmaster;

--
-- Name: ipv4_allow_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.ipv4_allow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ipv4_allow_id_seq OWNER TO cryptmaster;

--
-- Name: ipv4_allow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.ipv4_allow_id_seq OWNED BY public.ipv4_allow.id;


--
-- Name: ipv4_blacklist; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.ipv4_blacklist (
    id integer NOT NULL,
    ipv4_address character varying NOT NULL,
    date_added timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.ipv4_blacklist OWNER TO cryptmaster;

--
-- Name: ipv4_blacklist_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.ipv4_blacklist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ipv4_blacklist_id_seq OWNER TO cryptmaster;

--
-- Name: ipv4_blacklist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.ipv4_blacklist_id_seq OWNED BY public.ipv4_blacklist.id;


--
-- Name: secret_acl; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.secret_acl (
    id integer NOT NULL,
    server integer NOT NULL,
    secret integer NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.secret_acl OWNER TO cryptmaster;

--
-- Name: secret_acl_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.secret_acl_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.secret_acl_id_seq OWNER TO cryptmaster;

--
-- Name: secret_acl_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.secret_acl_id_seq OWNED BY public.secret_acl.id;


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
-- Name: system_info; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.system_info (
    id integer NOT NULL,
    install_date timestamp with time zone DEFAULT now() NOT NULL,
    version_active character varying NOT NULL,
    previous_version character varying DEFAULT 'none'::character varying NOT NULL
);


ALTER TABLE public.system_info OWNER TO cryptmaster;

--
-- Name: system_info_id_seq; Type: SEQUENCE; Schema: public; Owner: cryptmaster
--

CREATE SEQUENCE public.system_info_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.system_info_id_seq OWNER TO cryptmaster;

--
-- Name: system_info_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: cryptmaster
--

ALTER SEQUENCE public.system_info_id_seq OWNED BY public.system_info.id;


--
-- Name: user_accounts; Type: TABLE; Schema: public; Owner: cryptmaster
--

CREATE TABLE public.user_accounts (
    id integer NOT NULL,
    username character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    user_otp_hash character varying NOT NULL,
    active_until timestamp with time zone DEFAULT (now() + '365 days'::interval) NOT NULL,
    date_added timestamp with time zone DEFAULT now() NOT NULL
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
-- Name: cryptmaster_warden id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.cryptmaster_warden ALTER COLUMN id SET DEFAULT nextval('public.cryptmaster_warden_id_seq'::regclass);


--
-- Name: event_log id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.event_log ALTER COLUMN id SET DEFAULT nextval('public.event_log_id_seq'::regclass);


--
-- Name: ipv4_allow id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.ipv4_allow ALTER COLUMN id SET DEFAULT nextval('public.ipv4_allow_id_seq'::regclass);


--
-- Name: ipv4_blacklist id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.ipv4_blacklist ALTER COLUMN id SET DEFAULT nextval('public.ipv4_blacklist_id_seq'::regclass);


--
-- Name: secret_acl id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.secret_acl ALTER COLUMN id SET DEFAULT nextval('public.secret_acl_id_seq'::regclass);


--
-- Name: secrets id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.secrets ALTER COLUMN id SET DEFAULT nextval('public.secrets_id_seq'::regclass);


--
-- Name: system_info id; Type: DEFAULT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.system_info ALTER COLUMN id SET DEFAULT nextval('public.system_info_id_seq'::regclass);


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
-- Name: system_info cm_control_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.system_info
    ADD CONSTRAINT cm_control_pkey PRIMARY KEY (id);


--
-- Name: cryptmaster_warden cm_status_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.cryptmaster_warden
    ADD CONSTRAINT cm_status_pkey PRIMARY KEY (id);


--
-- Name: event_log event_log_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.event_log
    ADD CONSTRAINT event_log_pkey PRIMARY KEY (id);


--
-- Name: ipv4_allow ipv4_acl_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.ipv4_allow
    ADD CONSTRAINT ipv4_acl_pkey PRIMARY KEY (id);


--
-- Name: ipv4_blacklist ipv4_blacklist_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.ipv4_blacklist
    ADD CONSTRAINT ipv4_blacklist_pkey PRIMARY KEY (id);


--
-- Name: secrets secrets_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.secrets
    ADD CONSTRAINT secrets_pkey PRIMARY KEY (id);


--
-- Name: secret_acl server_secret_allow_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.secret_acl
    ADD CONSTRAINT server_secret_allow_pkey PRIMARY KEY (id);


--
-- Name: user_accounts user_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.user_accounts
    ADD CONSTRAINT user_accounts_pkey PRIMARY KEY (id);


--
-- Name: user_accounts user_accounts_unique; Type: CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.user_accounts
    ADD CONSTRAINT user_accounts_unique UNIQUE (username);


--
-- Name: event_log event_log_ipv4_allow_fk; Type: FK CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.event_log
    ADD CONSTRAINT event_log_ipv4_allow_fk FOREIGN KEY (linked_ipv4_wl) REFERENCES public.ipv4_allow(id);


--
-- Name: event_log event_log_ipv4_blacklist_fk; Type: FK CONSTRAINT; Schema: public; Owner: cryptmaster
--

ALTER TABLE ONLY public.event_log
    ADD CONSTRAINT event_log_ipv4_blacklist_fk FOREIGN KEY (linked_ipv4_bl) REFERENCES public.ipv4_blacklist(id);


--
-- PostgreSQL database dump complete
--