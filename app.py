import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    try:
        from vadersentiment import SentimentIntensityAnalyzer
    except ImportError:
        # Fallback if library is not installed correctly
        class SentimentIntensityAnalyzer:
            def polarity_scores(self, text):
                return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Pro Finance Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# --- Sidebar Configuration ---
st.sidebar.header("🎯 Ticker Selection")
ticker_symbol = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").upper()
time_period = st.sidebar.selectbox(
    "Select Time Period",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=3
)

st.sidebar.divider()
st.sidebar.header("📊 Benchmarking")
show_sp500 = st.sidebar.checkbox("Compare with S&P 500", value=True)
show_sector = st.sidebar.checkbox("Compare with Industry Average", value=True)

# Sector to ETF Mapping
SECTOR_MAP = {
    'Technology': 'XLK',
    'Financial Services': 'XLF',
    'Healthcare': 'XLV',
    'Consumer Cyclical': 'XLY',
    'Energy': 'XLE',
    'Industrials': 'XLI',
    'Consumer Defensive': 'XLP',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
    'Basic Materials': 'XLB',
    'Communication Services': 'XLC'
}

st.sidebar.divider()
st.sidebar.header("📰 News Filter")
news_search = st.sidebar.text_input("Search News", placeholder="e.g. Earnings, AI, Dividend")

# --- Data Fetching Functions ---
@st.cache_data(ttl=3600)
def fetch_stock_info(ticker):
    try:
        temp_session = requests.Session()
        temp_session.headers.update({'User-Agent': 'Mozilla/5.0'})
        stock = yf.Ticker(ticker, session=temp_session)
        info = stock.info
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
            return None
        return info
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_history(ticker, period):
    temp_session = requests.Session()
    temp_session.headers.update({'User-Agent': 'Mozilla/5.0'})
    stock = yf.Ticker(ticker, session=temp_session)
    return stock.history(period=period)

@st.cache_data(ttl=3600)
def fetch_news(ticker):
    try:
        # Ticker news doesn't always need the session and can be finicky
        stock = yf.Ticker(ticker)
        return stock.news
    except Exception:
        return []

# --- Helper Functions ---
def get_item_content(item, keys, default="Content not available"):
    for key in keys:
        if item.get(key):
            return item.get(key)
    return default

def calculate_rsi(data, window=14):
    try:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    except:
        return pd.Series()

def format_large_number(num):
    if num is None or pd.isna(num): return "N/A"
    try:
        if num >= 1_000_000_000_000: return f"{num/1_000_000_000_000:.2f}T"
        elif num >= 1_000_000_000: return f"{num/1_000_000_000:.2f}B"
        elif num >= 1_000_000: return f"{num/1_000_000:.2f}M"
        return str(round(num, 2))
    except:
        return str(num)

# --- Main Application ---
st.title(f"💎 Pro Finance Dashboard: {ticker_symbol}")

if ticker_symbol:
    info = fetch_stock_info(ticker_symbol)
    hist = fetch_history(ticker_symbol, time_period)
    
    if info and not hist.empty:
        # 1. Company Header
        col_header, col_price = st.columns([3, 1])
        with col_header:
            st.markdown(f"### {info.get('longName', ticker_symbol)}")
            st.caption(f"{info.get('sector', 'N/A')} | {info.get('industry', 'N/A')} | {info.get('country', 'N/A')}")
        
        with col_price:
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            prev_close = info.get('previousClose')
            if price and prev_close:
                change = price - prev_close
                change_pct = (change / prev_close) * 100
                st.metric("Price", f"${price:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")

        # 2. Key Metrics & Health Check
        st.markdown("---")
        m_col1, m_col2 = st.columns([1, 1])
        
        with m_col1:
            with st.container(border=True):
                st.subheader("🏥 Fundamental Health Check")
                # Health Logic
                current_ratio = info.get('currentRatio')
                debt_to_equity = info.get('debtToEquity')
                profit_margin = info.get('profitMargins')
                
                hc1, hc2, hc3 = st.columns(3)
                
                def health_indicator(val, threshold, high_is_good=True):
                    if val is None or pd.isna(val): return "⚪ N/A"
                    try:
                        if high_is_good:
                            return "🟢 Good" if val > threshold else "🔴 Weak"
                        else:
                            return "🟢 Good" if val < threshold else "🔴 High"
                    except:
                        return "⚪ N/A"

                hc1.write("**Liquidity**")
                hc1.write(f"{current_ratio:.2f}" if current_ratio else "N/A")
                hc1.write(health_indicator(current_ratio, 1.5))
                
                hc2.write("**Debt/Equity**")
                hc2.write(f"{debt_to_equity:.2f}" if debt_to_equity else "N/A")
                hc2.write(health_indicator(debt_to_equity, 100, False))
                
                hc3.write("**Profit Margin**")
                hc3.write(f"{profit_margin*100:.1f}%" if profit_margin else "N/A")
                hc3.write(health_indicator(profit_margin, 0.1))

        with m_col2:
            with st.container(border=True):
                st.subheader("📊 Valuations")
                v1, v2, v3 = st.columns(3)
                v1.metric("Market Cap", format_large_number(info.get('marketCap')))
                v2.metric("P/E Ratio", round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "N/A")
                v3.metric("Forward P/E", round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "N/A")

        # 3. Simple Performance Chart
        st.markdown("---")
        with st.container(border=True):
            st.subheader("📈 Performance Benchmarking")
            
            fig = go.Figure()
            
            # Helper to normalize series to % change
            def normalize(series):
                start_val = series.dropna().iloc[0]
                return ((series / start_val) - 1) * 100

            # 1. Main Ticker Performance
            fig.add_trace(go.Scatter(
                x=hist.index, 
                y=normalize(hist['Close']), 
                name=f'{ticker_symbol} %', 
                line=dict(color='#007bff', width=3)
            ))

            # 2. S&P 500 Benchmarking
            if show_sp500:
                sp500 = fetch_history("^GSPC", time_period)
                if not sp500.empty:
                    fig.add_trace(go.Scatter(
                        x=sp500.index, 
                        y=normalize(sp500['Close']), 
                        name='S&P 500 %', 
                        line=dict(color='red', width=1, dash='dot')
                    ))

            # 3. Industry Average (Sector ETF)
            if show_sector:
                sector = info.get('sector')
                etf_ticker = SECTOR_MAP.get(sector)
                if etf_ticker:
                    sector_data = fetch_history(etf_ticker, time_period)
                    if not sector_data.empty:
                        fig.add_trace(go.Scatter(
                            x=sector_data.index, 
                            y=normalize(sector_data['Close']), 
                            name=f'Ind. Avg ({etf_ticker}) %', 
                            line=dict(color='orange', width=1.5, dash='dash')
                        ))

            fig.update_layout(
                height=500,
                template="plotly_white",
                hovermode="x unified",
                yaxis_title="Total Return (%)",
                xaxis_title="Date",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        # 4. News & Sentiment Analysis
        st.markdown("---")
        st.subheader("📰 Latest News & Sentiment")
        news = fetch_news(ticker_symbol)
        
        if news:
            # Automatic Relevance Filtering
            # We look for the ticker OR the company name in the headline
            company_name_parts = info.get('longName', '').split(' ')[:2] # Get first two words of company name
            search_terms = [ticker_symbol.lower()] + [p.lower() for p in company_name_parts if len(p) > 2]
            
            filtered_news = []
            for item in news:
                content = item.get('content', item)
                title = get_item_content(content, ['title', 'headline', 'text'], '').lower()
                
                # If news_search is used, use that. Otherwise, use our automatic relevance filter
                if news_search:
                    if news_search.lower() in title:
                        filtered_news.append(item)
                else:
                    # Check if any search term (ticker or company name) is in the title
                    if any(term in title for term in search_terms):
                        filtered_news.append(item)
            
            # If our strict filter removed everything, fallback to original news but show a note
            # This ensures the dashboard isn't empty if yfinance news is slightly off
            display_news = filtered_news if filtered_news else news[:5]
            is_fallback = not filtered_news and news
            
            if is_fallback:
                st.caption("Showing most recent related news (no direct ticker mentions found).")

            n_col1, n_col2 = st.columns([2, 1])
            with n_col1:
                for i, item in enumerate(display_news[:5]):
                    with st.container(border=True):
                        content = item.get('content', item)
                        title = get_item_content(content, ['title', 'headline', 'text'], 'No Title Available')
                        raw_link = get_item_content(content, ['canonicalUrl', 'url', 'link'], '#')
                        link = str(raw_link) if raw_link else '#'
                        
                        st.write(f"**{title}**")
                        if link.startswith('http'):
                            st.link_button("Read Full Story", link)
                        
                        # Sentiment Logic
                        sentiment = analyzer.polarity_scores(str(title))
                        score = sentiment['compound']
                        
                        if score >= 0.05:
                            st.markdown("Sentiment: 🟢 **Positive**")
                        elif score <= -0.05:
                            st.markdown("Sentiment: 🔴 **Negative**")
                        else:
                            st.markdown("Sentiment: ⚪ **Neutral**")
            
            with n_col2:
                # Aggregate Sentiment (based on displayed news)
                news_titles = [get_item_content(n.get('content', n), ['title', 'headline', 'text'], '') for n in display_news]
                all_text = " ".join([str(t) for t in news_titles if t])
                overall = analyzer.polarity_scores(all_text) if all_text else {'compound': 0.0}
                
                st.markdown("### Market Sentiment")
                st.metric("Sentiment Score", f"{overall['compound']:+.2f}")
                st.info("The score evaluates the tone of the headlines shown on the left.")
        else:
            st.write("No news found for this ticker.")

    else:
        st.error(f"Could not find data for ticker: {ticker_symbol}. Ensure it's a valid Yahoo Finance ticker (e.g., AAPL, TSLA, ^GSPC).")

# Footer
st.sidebar.divider()
st.sidebar.caption("Built for Portfolio | Data: Yahoo Finance")
