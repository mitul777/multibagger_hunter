# =============================================================================
# midsmall_universe.py — Mid & Small Cap NSE Universe for Early Moat Detection
# =============================================================================
# Coverage: ~220 NSE-listed stocks across high-conviction sectors
# Market Cap Focus: ₹300 Cr — ₹30,000 Cr (smallcap + midcap)
#
# Sector logic: Focus on sectors where moats can be built early:
#   • Specialty Chemicals    — niche chemistry = switching costs + scale barriers
#   • CDMO / Niche Pharma   — regulated markets + IP = durable advantage
#   • Defense & Aerospace    — sole-source supply + long order books
#   • Electronics Mfg (EMS) — complex supply chains = stickiness
#   • Diagnostics Networks  — geographic density = local monopoly
#   • Niche IT / SaaS       — vertical-specific software = switching costs
#   • Specialty Finance     — underserved niches = pricing power
#   • Niche Consumer        — brand in focused category = pricing power
#   • Capital Goods Niche   — sole-supplier industrial products
#   • Logistics Infra       — network density = cost advantage
# =============================================================================

MIDSMALL_UNIVERSE = {

    # -----------------------------------------------------------------------
    # Specialty Chemicals — highest moat potential in Indian midcap
    # -----------------------------------------------------------------------
    "Specialty Chemicals": [
        "DEEPAKNTR.NS",    # Deepak Nitrite — phenol/acetone backward integration
        "FINEORG.NS",      # Fine Organics — oleochemical niche, export-led
        "NAVINFLUOR.NS",   # Navin Fluorine — specialty fluorine chemistry
        "VINATIORGA.NS",   # Vinati Organics — ATBS global leader
        "ALKYLAMINE.NS",   # Alkyl Amines — methyl amines niche
        "GALAXYSURF.NS",   # Galaxy Surfactants — green surfactants
        "CLEAN.NS",        # Clean Science — MEHQ/BHA monopoly
        "PIIND.NS",        # PI Industries — CSM agrochem, Japan tie-ups
        "BAYERCROP.NS",    # Bayer CropScience — branded agrochem
        "JUBLINGREA.NS",   # Jubilant Ingrevia — acetic anhydride leader
        "GNFC.NS",         # GNFC — TDI/acetic acid
        "SRF.NS",          # SRF — refrigerant gases + specialty films
        "TATACHEM.NS",     # Tata Chemicals — soda ash + specialty nutrition
        "ATUL.NS",         # Atul Ltd — diversified specialty
        "DHANUKA.NS",      # Dhanuka Agritech — branded agrochem distribution
        "INSECTICID.NS",   # Insecticides India — branded agrochem
        "HERANBA.NS",      # Heranba Industries — pyrethroid chemistry
    ],

    # -----------------------------------------------------------------------
    # CDMO / Specialty Pharma — contract manufacturing = sticky revenue
    # -----------------------------------------------------------------------
    "CDMO & Specialty Pharma": [
        "SUVEN.NS",        # Suven Pharmaceuticals — CDMO, NCE pipeline
        "SOLARA.NS",       # Solara Active Pharma — ibuprofen API leader
        "APLLTD.NS",       # Alembic Pharma — US generics + branded
        "CAPLIPOINT.NS",   # Caplin Point Labs — LATAM + Africa niche
        "JBCHEPHARM.NS",   # JB Chemicals — branded formulations
        "GRANULES.NS",     # Granules India — paracetamol API scale
        "LAURUSLABS.NS",   # Laurus Labs — ARV API + CDMO
        "NATCOPHARM.NS",   # Natco Pharma — Para IV first-filer
        "SEQUENT.NS",      # SeQuent Scientific — animal health API
        "STRIDES.NS",      # Strides Pharma — regulated market generics
        "MEDPLUS.NS",      # Medplus Health — pharmacy chain network
        "VIJAYA.NS",       # Vijaya Diagnostics — south India diagnostics
        "RAINBOWCHIL.NS",  # Rainbow Children's Hospital — pediatric niche
        "KIMS.NS",         # KIMS Hospitals — Andhra/Telangana network
    ],

    # -----------------------------------------------------------------------
    # Defense & Aerospace — sole source + long order book = durable revenue
    # -----------------------------------------------------------------------
    "Defense & Aerospace": [
        "HAL.NS",          # Hindustan Aeronautics — aircraft MRO + mfg
        "BEL.NS",          # Bharat Electronics — defense electronics
        "DATAPATTNS.NS",   # Data Patterns — defense electronics systems
        "MTARTECH.NS",     # MTAR Technologies — precision mfg for space/nuclear
        "GRSE.NS",         # Garden Reach Shipbuilders — naval vessels
        "COCHINSHIP.NS",   # Cochin Shipyard — LPG tankers + defense
        "PARAS.NS",        # Paras Defence — defense optics + EMP
        "BEML.NS",         # BEML — defense vehicles + metro rail
        "MIDHANI.NS",      # Mishra Dhatu Nigam — superalloys for defense
        "ZENTEC.NS",       # Zen Technologies — defense training simulators
        "IDEAFORGE.NS",    # ideaForge Technology — drone leader
        "SOLARINDS.NS",    # Solar Industries — explosives + defense ammo
    ],

    # -----------------------------------------------------------------------
    # Electronics Manufacturing Services (EMS) — India's manufacturing moat
    # -----------------------------------------------------------------------
    "Electronics Manufacturing (EMS)": [
        "DIXON.NS",        # Dixon Technologies — largest EMS player
        "AMBER.NS",        # Amber Enterprises — AC components + EMS
        "KAYNES.NS",       # Kaynes Technology — IoT + industrial EMS
        "SYRMA.NS",        # Syrma SGS Technology — PCB + EMS
        "PGIL.NS",         # Pearl Global — apparel manufacturing
        "AVALON.NS",       # Avalon Technologies — hi-rel EMS
        "VGUARD.NS",       # V-Guard Industries — consumer electricals
        "POLYCAB.NS",      # Polycab — wires + EMS (also large cap)
    ],

    # -----------------------------------------------------------------------
    # Niche IT / SaaS / Platforms — vertical dominance = switching cost moat
    # -----------------------------------------------------------------------
    "Niche IT & Platforms": [
        "TANLA.NS",        # Tanla Platforms — CPaaS platform (telecom)
        "NEWGEN.NS",       # Newgen Software — BPM/ECM enterprise software
        "INTELLECT.NS",    # Intellect Design Arena — banking software
        "ROUTE.NS",        # Route Mobile — CPaaS + cloud comms
        "AURIONPRO.NS",    # Aurionpro Solutions — banking/transit tech
        "KFINTECH.NS",     # KFin Technologies — registrar monopoly (KRA)
        "BSOFT.NS",        # Birlasoft — enterprise IT
        "CYIENT.NS",       # Cyient — engineering services + geospatial
        "ZENSAR.NS",       # Zensar Technologies — mid-market IT
        "NAUKRI.NS",       # Info Edge (Naukri) — job portal network effect
        "IRCTC.NS",        # IRCTC — rail ticketing monopoly
        "CDSL.NS",         # CDSL — depository (regulatory monopoly)
        "CAMS.NS",         # CAMS — MF registrar duopoly
        "MCX.NS",          # MCX — commodity exchange
    ],

    # -----------------------------------------------------------------------
    # Specialty Finance — underserved niches = pricing power + low competition
    # -----------------------------------------------------------------------
    "Specialty Finance": [
        "FIVESTAR.NS",     # Five Star Business Finance — MSME lending niche
        "APTUS.NS",        # Aptus Value Housing Finance — rural housing
        "HOMEFIRST.NS",    # Home First Finance — affordable housing
        "SBFC.NS",         # SBFC Finance — MSME secured lending
        "CREDITACC.NS",    # CreditAccess Grameen — microfinance
        "SPANDANA.NS",     # Spandana Sphoorty — microfinance
        "IIFLWAM.NS",      # IIFL Wealth Management — HNI wealth
        "360ONE.NS",       # 360 ONE WAM — ultra-HNI wealth
        "CAMS.NS",         # CAMS (also in IT)
        "KFINTECH.NS",     # KFin (also in IT)
        "NIPPOBATRY.NS",   # Nippo Batteries — niche industrial
    ],

    # -----------------------------------------------------------------------
    # Niche Consumer / Branded Plays — brand in focused category
    # -----------------------------------------------------------------------
    "Niche Consumer & Brands": [
        "PAGEIND.NS",      # Page Industries — Jockey brand monopoly
        "TRENT.NS",        # Trent — Zara + Westside retail rollout
        "BIKAJI.NS",       # Bikaji Foods — ethnic snacks leader
        "PRATAAP.NS",      # Prataap Snacks — Yellow Diamond brand
        "CAMPUS.NS",       # Campus Activewear — affordable sports footwear
        "METROBRAND.NS",   # Metro Brands — footwear retail network
        "VEDANT.NS",       # Vedant Fashions (Manyavar) — ethnic wear moat
        "GODFRYPHLP.NS",   # Godfrey Phillips — tobacco niche
        "RADICO.NS",       # Radico Khaitan — prestige spirits
        "UNITDSPR.NS",     # United Spirits — premium spirits portfolio
        "WESTLIFE.NS",     # Westlife Foodworld — McDonald's master franchise
        "DEVYANI.NS",      # Devyani International — KFC/Pizza Hut franchise
        "SAPPHIRE.NS",     # Sapphire Foods — KFC franchise operator
        "RELAXO.NS",       # Relaxo Footwears — mass market footwear
    ],

    # -----------------------------------------------------------------------
    # Capital Goods & Niche Engineering — precision = barriers to entry
    # -----------------------------------------------------------------------
    "Niche Capital Goods & Engineering": [
        "GRINDWELL.NS",    # Grindwell Norton — abrasives leader (Saint-Gobain)
        "TIMKEN.NS",       # Timken India — bearings for rail/industrial
        "SCHAEFFLER.NS",   # Schaeffler India — precision bearings
        "CUMMINSIND.NS",   # Cummins India — diesel engine leader
        "RATNAMANI.NS",    # Ratnamani Metals — stainless steel tubes
        "ISGEC.NS",        # ISGEC Heavy Engineering — custom heavy equipment
        "KEC.NS",          # KEC International — power transmission towers
        "KALPATPOWR.NS",   # Kalpataru Power — T&D EPC leader
        "TRITURBINE.NS",   # Triveni Turbine — steam turbine niche
        "JYOTICNC.NS",     # Jyoti CNC — CNC machine tools
        "ELECON.NS",       # Elecon Engineering — gears + MHE
        "ELGIEQUIP.NS",    # Elgi Equipments — compressors (global niche)
        "ASTRAL.NS",       # Astral Ltd — CPVC pipes + adhesives
        "SUPREMEIND.NS",   # Supreme Industries — plastic products
        "APLAPOLLO.NS",    # APL Apollo Tubes — structural steel tubes
        "WELSPUNIND.NS",   # Welspun India — home textiles (global scale)
        "TRIDENT.NS",      # Trident Group — Terry towels + paper
    ],

    # -----------------------------------------------------------------------
    # Specialty Logistics & Infra — network density = cost moat
    # -----------------------------------------------------------------------
    "Specialty Logistics": [
        "TCIEXP.NS",       # TCI Express — express logistics network
        "DELHIVERY.NS",    # Delhivery — ecommerce logistics platform
        "MAHLOG.NS",       # Mahindra Logistics — 3PL + EV last mile
        "GATI.NS",         # Gati Ltd — express parcel
        "TVSSCS.NS",       # TVS Supply Chain — integrated supply chain
        "CONCOR.NS",       # Container Corporation — rail-based logistics moat
        "ADANIPORTS.NS",   # Adani Ports — port network
    ],

    # -----------------------------------------------------------------------
    # Niche Healthcare Infrastructure
    # -----------------------------------------------------------------------
    "Healthcare Infrastructure": [
        "NARAYANA.NS",     # Narayana Hrudayalaya — cardiac care volume model
        "RAINBOWCHIL.NS",  # Rainbow Children's — pediatric specialty
        "VIJAYA.NS",       # Vijaya Diagnostics — South India diagnostics
        "METROPOLIS.NS",   # Metropolis Healthcare (also in pharma)
        "KIMS.NS",         # KIMS Hospitals
        "MEDPLUS.NS",      # Medplus pharmacy chain
    ],

    # -----------------------------------------------------------------------
    # Water, Environment & Clean Tech — government mandate + niche tech
    # -----------------------------------------------------------------------
    "Clean Tech & Environment": [
        "VATECH.NS",       # VA Tech Wabag — water treatment EPC
        "IONEXCHANG.NS",   # Ion Exchange India — water treatment chemicals
        "INOXWIND.NS",     # Inox Wind — wind turbines
        "GEPIL.NS",        # GE Power India — power equipment
        "CESC.NS",         # CESC — utility + renewable push
    ],
}

# Flat universe list
ALL_MIDSMALL_STOCKS = [
    ticker
    for sector_list in MIDSMALL_UNIVERSE.values()
    for ticker in sector_list
]

# Remove duplicates while preserving order
seen = set()
ALL_MIDSMALL_STOCKS = [
    t for t in ALL_MIDSMALL_STOCKS
    if not (t in seen or seen.add(t))
]

# -----------------------------------------------------------------------
# Sector to "Moat Type" mapping — helps context-aware scoring
# -----------------------------------------------------------------------
SECTOR_MOAT_TYPE = {
    "Specialty Chemicals":           "switching_cost + scale",
    "CDMO & Specialty Pharma":       "regulatory + ip",
    "Defense & Aerospace":           "sole_source + order_book",
    "Electronics Manufacturing (EMS)": "switching_cost + complexity",
    "Niche IT & Platforms":          "switching_cost + network_effect",
    "Specialty Finance":             "niche + underserved_market",
    "Niche Consumer & Brands":       "brand + pricing_power",
    "Niche Capital Goods & Engineering": "precision + certification",
    "Specialty Logistics":           "network_density + cost_advantage",
    "Healthcare Infrastructure":     "network + geography",
    "Clean Tech & Environment":      "regulatory + niche_tech",
}

# -----------------------------------------------------------------------
# Hard filter overrides for smallcap / midcap
# -----------------------------------------------------------------------
MIDSMALL_HARD_FILTERS = {
    "min_market_cap_cr":   300,    # ₹300 Cr min (avoids micro-cap illiquidity)
    "max_market_cap_cr": 30_000,   # ₹30,000 Cr max (still mid/smallcap)
    "min_revenue_cr":      100,    # ₹100 Cr min revenue
    "max_debt_equity":       2.0,  # Slightly relaxed vs. large cap screen
    "min_roce_pct":          8.0,  # Lower threshold — early-stage moat companies
    "min_years_data":        2,    # At least 2 years of history
    "max_years_data_for_bonus": 5, # Penalise if no trajectory visible
}
