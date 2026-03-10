"""
Generate PDF guide: Admitad Affiliate Programs for Pinterest Marketing
"""
from fpdf import FPDF


class GuidePDF(FPDF):
    ACCENT = (52, 101, 164)      # steel blue
    DARK = (33, 33, 33)
    LIGHT_BG = (245, 247, 250)
    WHITE = (255, 255, 255)
    GREEN = (39, 137, 68)
    RED = (180, 50, 50)
    ORANGE = (210, 130, 30)
    GRAY = (120, 120, 120)
    F = "Segoe"  # font family alias

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        font_dir = "C:/Windows/Fonts"
        self.add_font("Segoe", "", f"{font_dir}/segoeui.ttf", uni=True)
        self.add_font("Segoe", "B", f"{font_dir}/segoeuib.ttf", uni=True)
        self.add_font("Segoe", "I", f"{font_dir}/segoeuii.ttf", uni=True)

    def header(self):
        if self.page_no() > 1:
            self.set_font(self.F, "I", 8)
            self.set_text_color(*self.GRAY)
            self.cell(0, 8, "PrismAffiliate \u2014 Admitad Programs Guide for Pinterest", align="R")
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.F, "I", 8)
        self.set_text_color(*self.GRAY)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.ln(6)
        self.set_font(self.F, "B", 15)
        self.set_text_color(*self.ACCENT)
        self.cell(0, 10, title)
        self.ln(8)
        # underline
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

    def sub_title(self, title: str):
        self.ln(3)
        self.set_font(self.F, "B", 12)
        self.set_text_color(*self.DARK)
        self.cell(0, 8, title)
        self.ln(7)

    def body_text(self, text: str):
        self.set_font(self.F, "", 10)
        self.set_text_color(*self.DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text: str, bold_prefix: str = ""):
        self.set_font(self.F, "", 10)
        self.set_text_color(*self.DARK)
        x = self.get_x()
        self.cell(6, 5.5, chr(8226))  # bullet char
        if bold_prefix:
            self.set_font(self.F, "B", 10)
            self.cell(self.get_string_width(bold_prefix) + 1, 5.5, bold_prefix)
            self.set_font(self.F, "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def tier_badge(self, tier: str, color: tuple):
        self.set_fill_color(*color)
        self.set_text_color(*self.WHITE)
        self.set_font(self.F, "B", 11)
        w = self.get_string_width(tier) + 12
        self.cell(w, 8, f"  {tier}", fill=True)
        self.ln(6)

    def program_card(self, name, niche, approval, cr, epc, commission, geo, why):
        # card background
        y_start = self.get_y()
        if y_start > 245:
            self.add_page()
            y_start = self.get_y()

        self.set_fill_color(*self.LIGHT_BG)
        self.rect(self.l_margin, y_start, self.w - self.l_margin - self.r_margin, 38, "F")

        self.set_xy(self.l_margin + 3, y_start + 2)
        self.set_font(self.F, "B", 11)
        self.set_text_color(*self.ACCENT)
        self.cell(90, 6, name)

        # badges
        self.set_font(self.F, "", 8)
        # approval badge
        self.set_fill_color(*self.GREEN)
        self.set_text_color(*self.WHITE)
        badge = f"Approval {approval}"
        self.cell(self.get_string_width(badge) + 6, 5, badge, fill=True)
        self.cell(2, 5, "")
        # CR badge
        self.set_fill_color(*self.ORANGE)
        badge2 = f"CR {cr}"
        self.cell(self.get_string_width(badge2) + 6, 5, badge2, fill=True)
        self.cell(2, 5, "")
        # EPC badge
        self.set_fill_color(*self.ACCENT)
        badge3 = f"EPC {epc}"
        self.cell(self.get_string_width(badge3) + 6, 5, badge3, fill=True)
        self.ln(7)

        self.set_x(self.l_margin + 3)
        self.set_font(self.F, "", 9)
        self.set_text_color(*self.DARK)
        self.cell(45, 5, f"Niche: {niche}")
        self.cell(45, 5, f"Commission: {commission}")
        self.cell(0, 5, f"GEO: {geo}")
        self.ln(6)

        self.set_x(self.l_margin + 3)
        self.set_font(self.F, "I", 9)
        self.set_text_color(*self.GRAY)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 6, 5, f"Why: {why}")

        self.set_y(y_start + 40)

    def category_row(self, cat, reason, priority_color):
        y = self.get_y()
        if y > 265:
            self.add_page()
            y = self.get_y()
        self.set_fill_color(*priority_color)
        self.set_text_color(*self.WHITE)
        self.set_font(self.F, "B", 9)
        self.cell(3, 6, "", fill=True)
        self.set_text_color(*self.DARK)
        self.set_fill_color(*self.LIGHT_BG)
        self.set_font(self.F, "B", 10)
        self.cell(70, 6, f"  {cat}", fill=True)
        self.set_font(self.F, "", 9)
        self.cell(0, 6, f"  {reason}", fill=True)
        self.ln(7)

    def skip_row(self, cat, reason):
        y = self.get_y()
        if y > 265:
            self.add_page()
        self.set_font(self.F, "", 9)
        self.set_text_color(*self.RED)
        self.cell(3, 5.5, "X")
        self.set_text_color(*self.DARK)
        self.set_font(self.F, "B", 9)
        self.cell(70, 5.5, cat)
        self.set_font(self.F, "", 9)
        self.set_text_color(*self.GRAY)
        self.cell(0, 5.5, reason)
        self.ln(6)


def build():
    pdf = GuidePDF("P", "mm", "A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ============ COVER PAGE ============
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font(pdf.F, "B", 28)
    pdf.set_text_color(*pdf.ACCENT)
    pdf.cell(0, 14, "PrismAffiliate", align="C")
    pdf.ln(16)
    pdf.set_font(pdf.F, "", 16)
    pdf.set_text_color(*pdf.DARK)
    pdf.cell(0, 10, "Admitad Affiliate Programs Guide", align="C")
    pdf.ln(10)
    pdf.cell(0, 10, "for Pinterest Marketing", align="C")
    pdf.ln(25)
    pdf.set_draw_color(*pdf.ACCENT)
    pdf.set_line_width(0.8)
    mid = pdf.w / 2
    pdf.line(mid - 30, pdf.get_y(), mid + 30, pdf.get_y())
    pdf.ln(15)
    pdf.set_font(pdf.F, "", 11)
    pdf.set_text_color(*pdf.GRAY)
    pdf.cell(0, 7, "Which programs to JOIN and why", align="C")
    pdf.ln(7)
    pdf.cell(0, 7, "Optimized for Pinterest pin publishing pipeline", align="C")
    pdf.ln(7)
    pdf.cell(0, 7, "March 2026", align="C")

    # ============ PAGE 2: WHY PINTEREST ============
    pdf.add_page()
    pdf.section_title("1. Why Pinterest for Affiliate Marketing")
    pdf.body_text(
        "Pinterest is a visual discovery engine with 600M+ monthly active users (2025). "
        "Unlike social media feeds, Pinterest content has an extremely long shelf life - "
        "pins can drive traffic for months and even years after publishing."
    )
    pdf.sub_title("Pinterest Audience & Niches")
    pdf.bullet("79% of users are interested in Home Decor & Organization", "Home Decor: ")
    pdf.bullet("Fashion & Beauty - outfit ideas, skincare, lookbooks", "Fashion: ")
    pdf.bullet("Health & Wellness - vitamins, supplements, self-care", "Health: ")
    pdf.bullet("DIY & Gadgets - life hacks, smart home, tools", "DIY: ")
    pdf.bullet("Kids & Parenting - huge mom audience actively shopping", "Kids: ")
    pdf.bullet("Pets - emotional purchases, growing niche", "Pets: ")

    pdf.sub_title("Key Pinterest Metrics for Affiliates")
    pdf.bullet("Average pin lifespan: 3-6 months (vs 24h for Instagram)")
    pdf.bullet("85% of weekly Pinners have made a purchase from Pinterest pins")
    pdf.bullet("Pinterest users spend 80% more than non-Pinterest shoppers")
    pdf.bullet("Affiliate links are allowed directly in pins (no link-in-bio needed)")

    # ============ PAGE 3: CATEGORY SELECTION ============
    pdf.add_page()
    pdf.section_title("2. Admitad Categories to JOIN")
    pdf.body_text(
        "Below are all Admitad program categories sorted by priority for Pinterest marketing. "
        "Only join programs that have the Product Feed tool - this is essential for automated "
        "product ingestion into PrismAffiliate."
    )

    pdf.sub_title("Selection Criteria")
    pdf.bullet("Approval rate > 80% (lower = money stuck in hold)")
    pdf.bullet("Product Feed tool available (mandatory for automation)")
    pdf.bullet("Visual products (Pinterest is image-first)")
    pdf.bullet("Global GEO preferred (WW, Many GEOs)")
    pdf.bullet("Reasonable hold time (< 90 days ideal)")

    pdf.ln(3)
    pdf.sub_title("PRIORITY 1 - Join Immediately")
    pdf.body_text("These categories are the core of Pinterest affiliate marketing. "
                  "Every program with Product Feed in these categories is worth joining.")

    GREEN = (39, 137, 68)
    BLUE = (52, 101, 164)
    ORANGE_C = (210, 150, 50)

    cats_p1 = [
        ("Clothing, Footwear, Accessories",
         "Top Pinterest niche. Outfit pins, lookbooks, seasonal collections."),
        ("Furniture & Homeware",
         "79% of Pinterest users search home decor. Huge traffic potential."),
        ("Jewelry & Luxury Goods",
         "High AOV = big commission per sale. Visually stunning pins."),
        ("Marketplaces (incl. Chinese Stores)",
         "AliExpress, Banggood - massive catalogs covering all niches."),
        ("Personal Care & Pharmacy",
         "iHerb-type: beauty, skincare, vitamins. Top EPC ($32 for iHerb)."),
        ("Sports & Outdoor",
         "Fitness/lifestyle pins. Nike and similar - high brand trust = high CTR."),
    ]
    for cat, reason in cats_p1:
        pdf.category_row(cat, reason, GREEN)

    pdf.ln(3)
    pdf.sub_title("PRIORITY 2 - Join Next")
    pdf.body_text("Strong Pinterest niches with good conversion potential.")

    cats_p2 = [
        ("Toys, Kids & Babies",
         "Moms are a massive Pinterest audience, actively shopping."),
        ("Hobby & Stationery",
         "DIY, planners, craft supplies - extremely 'pinnable' content."),
        ("Smart Home",
         "Trending tech niche, gadgets for home - crossover with Home Decor."),
        ("Pets",
         "Emotional purchases, growing niche, cute = clicks."),
        ("Gifts & Flowers",
         "Seasonal spikes (holidays), gift guide pins go viral."),
    ]
    for cat, reason in cats_p2:
        pdf.category_row(cat, reason, BLUE)

    pdf.ln(3)
    pdf.sub_title("PRIORITY 3 - Add Later")
    cats_p3 = [
        ("Food & Food delivery",
         "Recipe pins + kitchen gadgets/specialty products."),
        ("Hand & Power tools",
         "DIY audience on Pinterest. Niche but dedicated."),
        ("Household Appliances & Electronics",
         "Selective - only visually appealing items (coffee machines, etc)."),
        ("Books",
         "Book recommendation pins work, but low commission."),
    ]
    for cat, reason in cats_p3:
        pdf.category_row(cat, reason, ORANGE_C)

    # ============ DO NOT JOIN ============
    pdf.add_page()
    pdf.section_title("3. Categories to SKIP")
    pdf.body_text(
        "These categories are not suitable for Pinterest affiliate marketing. "
        "Either the content is not visual, Pinterest restricts it, or the buying cycle is too long."
    )

    skips = [
        ("Travel & Tourism", "Services, not products. No Product Feed with items to pin."),
        ("Ridesharing & Taxi", "Not visual, not shoppable on Pinterest."),
        ("Financial Programs (all)", "Credits, loans, forex - not visual content."),
        ("Online Games (all)", "Not 'pinnable', wrong audience."),
        ("Mobile Programs (all)", "App installs don't work via Pinterest pins."),
        ("Dating Services", "Pinterest restricts, wrong audience."),
        ("Adult", "Pinterest strictly prohibits."),
        ("Tobacco", "Pinterest strictly prohibits."),
        ("Liquors", "Pinterest restricts alcohol content."),
        ("Cars & Bikes", "Very long purchase cycle, niche audience."),
        ("Car Loans / Mortgage", "Not visual, complex conversion."),
        ("IT Services & Soft", "B2B, not visual."),
        ("B2B Online Services", "Wrong audience entirely."),
        ("Jobs and freelance", "Not product-based."),
        ("Forex / Investments", "Regulated, not visual, Pinterest may restrict."),
        ("Online Education", "Low visual appeal for pins."),
        ("Telecommunications", "Not product-based, service subscriptions."),
        ("News and Media", "No affiliate product to sell."),
        ("Exclusives / Seasonal", "Temporary programs, not stable income."),
    ]
    for cat, reason in skips:
        pdf.skip_row(cat, reason)

    # ============ TOP PROGRAMS ============
    pdf.add_page()
    pdf.section_title("4. Top Recommended Programs (with Product Feed)")
    pdf.body_text(
        "These specific programs have been verified to have Product Feed support, "
        "high approval rates, and strong fit for Pinterest content."
    )

    pdf.ln(2)
    pdf.tier_badge("TIER 1 - Join First (Highest ROI)", pdf.GREEN)
    pdf.ln(2)

    pdf.program_card(
        "SHEIN Many GEOs",
        "Fashion & Beauty",
        "94%", "4%", "$13",
        "10-20% CPS",
        "40+ countries",
        "Highest commission in fashion. Massive catalog ideal for outfit/lookbook pins. "
        "Trendy affordable fashion = high conversion on Pinterest."
    )
    pdf.ln(2)
    pdf.program_card(
        "iHerb.com INT",
        "Health & Beauty",
        "93.8%", "6.4%", "$32",
        "up to 10% CPS",
        "50+ regions",
        "Best EPC of all programs ($32!). Vitamins, skincare, supplements - "
        "top Pinterest niche. High repeat purchase rate."
    )
    pdf.ln(2)
    pdf.program_card(
        "AliExpress WW",
        "Home / Fashion / Gadgets",
        "88.9%", "5.8%", "$3",
        "3-9% CPS",
        "200+ countries",
        "Enormous catalog covering ALL Pinterest niches. Home decor, gadgets, fashion. "
        "Low EPC but massive volume potential."
    )

    pdf.add_page()
    pdf.tier_badge("TIER 2 - Join Next (High AOV / Niche)", pdf.ACCENT)
    pdf.ln(2)

    pdf.program_card(
        "Farfetch Many GEOs",
        "Luxury Fashion",
        "85.6%", "0.1%", "$1",
        "up to 8% CPS",
        "180+ countries (no RU)",
        "AOV of 400 GBP - one sale = big commission. 2900+ luxury brands. "
        "Low CR but high reward. Best after relocating (Russia excluded)."
    )
    pdf.ln(2)
    pdf.program_card(
        "Banggood WW",
        "Home / Gadgets / DIY",
        "91.6%", "0.3%", "$2",
        "up to 8% CPS",
        "190+ countries",
        "Budget gadgets, home organization, DIY tools. "
        "Great for Pinterest organization/life hack pins."
    )
    pdf.ln(2)
    pdf.program_card(
        "Nike",
        "Fashion & Fitness",
        "~85%", "-", "-",
        "up to 8% CPS",
        "Multiple GEOs",
        "Iconic brand = high trust = high CTR on pins. "
        "Lifestyle and fitness content performs well on Pinterest."
    )

    # ============ HOW TO JOIN ============
    pdf.add_page()
    pdf.section_title("5. How to Join - Step by Step")

    pdf.sub_title("Step 1: Filter in Admitad Store")
    pdf.bullet("Go to Admitad Store > Catalog")
    pdf.bullet("Set filter: Tools = Product Feed")
    pdf.bullet("Set filter: Sort by Approval Rate (descending)")
    pdf.bullet("Browse categories from Priority 1 list above")

    pdf.sub_title("Step 2: Evaluate Each Program")
    pdf.bullet("Check Approval Rate > 80%")
    pdf.bullet("Check GEO coverage matches your target audience")
    pdf.bullet("Check Hold Time (shorter = faster payout)")
    pdf.bullet("Verify Product Feed is actually listed in Tools")
    pdf.bullet("Read traffic rules - ensure Pinterest / social media is allowed")

    pdf.sub_title("Step 3: Submit Join Request")
    pdf.bullet("Click 'Join' on each selected program")
    pdf.bullet("Some programs auto-approve, others take 1-7 days")
    pdf.bullet("While waiting, move to the next program")

    pdf.sub_title("Step 4: Configure in PrismAffiliate")
    pdf.bullet("Add Marketplace Account in PrismAffiliate UI (localhost:3001/accounts)")
    pdf.bullet("Enter Admitad credentials (client_id, client_secret, website_id, campaign_id)")
    pdf.bullet("Add Product Feed URL from Admitad program dashboard")
    pdf.bullet("Set feed sync schedule (default: every 6 hours)")
    pdf.bullet("Worker will auto-ingest products and push to Pinterest via PRISM")

    pdf.sub_title("Step 5: Monitor & Optimize")
    pdf.bullet("Track CTR per marketplace in PrismAffiliate analytics dashboard")
    pdf.bullet("Focus on programs with highest EPC (earnings per click)")
    pdf.bullet("Pause underperforming feeds, scale winners")
    pdf.bullet("Test different pin styles (5 background options: oat, indigo, cherry, sage, butter)")

    # ============ GEO STRATEGY ============
    pdf.add_page()
    pdf.section_title("6. GEO Strategy")

    pdf.sub_title("Phase 1: Now (from Russia)")
    pdf.body_text(
        "While in Russia, focus on programs with global GEO (WW / Many GEOs). "
        "Your Pinterest audience will be international - pins in English reach "
        "the broadest audience. Key programs:"
    )
    pdf.bullet("AliExpress WW (200+ countries)")
    pdf.bullet("SHEIN Many GEOs (40+ countries)")
    pdf.bullet("iHerb INT (50+ regions)")
    pdf.bullet("Banggood WW (190+ countries)")
    pdf.ln(2)
    pdf.body_text(
        "Note: Farfetch explicitly excludes Russia. Save it for after relocation."
    )

    pdf.sub_title("Phase 2: After Relocation")
    pdf.body_text(
        "Once you move, add local programs for your new country. "
        "Local programs often have higher commission rates and faster approval. "
        "Also add Farfetch Many GEOs at this point."
    )
    pdf.bullet("Join Farfetch Many GEOs (180+ countries, high AOV)")
    pdf.bullet("Add local marketplace programs for your new country")
    pdf.bullet("Adjust Pinterest content language if targeting local audience")
    pdf.bullet("Consider adding local Admitad programs (country-specific stores)")

    # ============ QUICK REFERENCE ============
    pdf.add_page()
    pdf.section_title("7. Quick Reference Card")

    pdf.sub_title("Programs Ranked by EPC")
    data_epc = [
        ("iHerb.com INT", "$32", "93.8%", "Health & Beauty"),
        ("SHEIN Many GEOs", "$13", "94%", "Fashion"),
        ("AliExpress WW", "$3", "88.9%", "Marketplace"),
        ("Banggood WW", "$2", "91.6%", "Gadgets/Home"),
        ("Farfetch Many GEOs", "$1", "85.6%", "Luxury Fashion"),
    ]

    # Table header
    pdf.set_font(pdf.F, "B", 9)
    pdf.set_fill_color(*pdf.ACCENT)
    pdf.set_text_color(*pdf.WHITE)
    pdf.cell(55, 7, "  Program", fill=True)
    pdf.cell(20, 7, "EPC", fill=True, align="C")
    pdf.cell(25, 7, "Approval", fill=True, align="C")
    pdf.cell(0, 7, "Niche", fill=True)
    pdf.ln(7)

    pdf.set_font(pdf.F, "", 9)
    pdf.set_text_color(*pdf.DARK)
    for i, (name, epc, appr, niche) in enumerate(data_epc):
        bg = pdf.LIGHT_BG if i % 2 == 0 else pdf.WHITE
        pdf.set_fill_color(*bg)
        pdf.cell(55, 6, f"  {name}", fill=True)
        pdf.cell(20, 6, epc, fill=True, align="C")
        pdf.cell(25, 6, appr, fill=True, align="C")
        pdf.cell(0, 6, niche, fill=True)
        pdf.ln(6)

    pdf.ln(5)
    pdf.sub_title("Categories Cheatsheet")
    pdf.set_font(pdf.F, "B", 9)
    pdf.set_text_color(*pdf.GREEN)
    pdf.cell(0, 6, "JOIN (Priority 1):")
    pdf.ln(5)
    pdf.set_font(pdf.F, "", 9)
    pdf.set_text_color(*pdf.DARK)
    pdf.body_text("Clothing/Footwear/Accessories | Furniture/Homeware | Jewelry/Luxury | "
                  "Marketplaces | Personal Care/Pharmacy | Sports/Outdoor")

    pdf.set_font(pdf.F, "B", 9)
    pdf.set_text_color(*pdf.ACCENT)
    pdf.cell(0, 6, "JOIN (Priority 2):")
    pdf.ln(5)
    pdf.set_font(pdf.F, "", 9)
    pdf.set_text_color(*pdf.DARK)
    pdf.body_text("Toys/Kids/Babies | Hobby/Stationery | Smart Home | Pets | Gifts/Flowers")

    pdf.set_font(pdf.F, "B", 9)
    pdf.set_text_color(*pdf.ORANGE)
    pdf.cell(0, 6, "JOIN LATER (Priority 3):")
    pdf.ln(5)
    pdf.set_font(pdf.F, "", 9)
    pdf.set_text_color(*pdf.DARK)
    pdf.body_text("Food/Delivery | Hand/Power Tools | Appliances/Electronics | Books")

    pdf.set_font(pdf.F, "B", 9)
    pdf.set_text_color(*pdf.RED)
    pdf.cell(0, 6, "SKIP:")
    pdf.ln(5)
    pdf.set_font(pdf.F, "", 9)
    pdf.set_text_color(*pdf.DARK)
    pdf.body_text("Travel | Finance | Games | Mobile | Dating | Adult | Tobacco | "
                  "Liquor | Cars | IT/B2B | Jobs | Telecom | News")

    # Output
    out_path = "e:/!PrismAffiliate/docs/Admitad_Pinterest_Guide.pdf"
    pdf.output(out_path)
    print(f"PDF saved to: {out_path}")


if __name__ == "__main__":
    build()
