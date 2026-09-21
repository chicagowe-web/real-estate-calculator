"""Core research engine orchestrating multi-source searches."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from .models import (
    ResearchResult,
    ResourceBundle,
    SourceType,
    Citation,
    VideoData,
    DetailLevel,
    CommentAnalysis,
)
from .searchers.web_search import WebSearcher
from .searchers.youtube import YouTubeSearcher
from .searchers.pdf_search import PDFSearcher
from .analyzers.comment_analyzer import CommentAnalyzer
from .synthesis.report_builder import ReportBuilder

logger = logging.getLogger("researchagent.research_engine")


class ResearchEngine:
    """Orchestrates multi-source research."""

    def __init__(self, detail_level: DetailLevel = DetailLevel.STANDARD):
        self.detail_level = detail_level
        self.web_searcher = WebSearcher()
        self.youtube_searcher = YouTubeSearcher()
        self.pdf_searcher = PDFSearcher()
        self.comment_analyzer = CommentAnalyzer()
        self.report_builder = ReportBuilder()

    async def research(self, topic: str) -> ResearchResult:
        """Execute comprehensive research on a topic.

        Args:
            topic: Research topic

        Returns:
            Complete research result with insights
        """
        logger.info(f"Starting research on: {topic}")

        # Run searches in parallel
        web_results, youtube_results, pdf_results = await asyncio.gather(
            self.web_searcher.search(topic, limit=10),
            self.youtube_searcher.search(topic, limit=5),
            self.pdf_searcher.search(topic, limit=5),
        )

        # Bundle resources
        resources = ResourceBundle(
            videos=youtube_results.get("videos", []),
            articles=web_results.get("articles", []),
            forum_posts=web_results.get("forum_posts", []),
            papers=pdf_results.get("papers", []),
        )

        # Analyze comments if detail level requires
        comment_analysis = None
        if self.detail_level in [DetailLevel.STANDARD, DetailLevel.COMPREHENSIVE]:
            comment_analysis = await self.comment_analyzer.analyze_comments(
                topic,
                videos=youtube_results.get("videos", []),
                forums=web_results.get("forum_posts", []),
            )

        # Build report with local GPU inference
        overview, best_practices, pitfalls, pro_tips, common_questions = await asyncio.gather(
            self.report_builder.generate_overview(topic, resources),
            self.report_builder.extract_practices(resources),
            self.report_builder.extract_pitfalls(resources),
            self.report_builder.extract_tips(resources),
            self.report_builder.extract_questions(comment_analysis),
        )

        # Create result
        result = ResearchResult(
            topic=topic,
            timestamp=datetime.utcnow(),
            overview=overview,
            detail_level=self.detail_level,
            resources=resources,
            best_practices=best_practices,
            pitfalls=pitfalls,
            pro_tips=pro_tips,
            common_questions=common_questions,
            comment_analysis=comment_analysis,
            sources_count=len(resources.all_citations()),
        )

        logger.info(f"Research complete. Found {result.sources_count} sources")
        return result

    async def deep_research(self, topic: str) -> ResearchResult:
        """Execute deep research with sentiment analysis and trends.

        Args:
            topic: Research topic

        Returns:
            Comprehensive research result
        """
        self.detail_level = DetailLevel.COMPREHENSIVE
        result = await self.research(topic)

        # Add deep analysis
        if result.comment_analysis:
            # Analyze sentiment trends
            pass

        return result


class QuickResearchEngine:
    """Lightweight research for quick lookups."""

    def __init__(self):
        self.web_searcher = WebSearcher()
        self.youtube_searcher = YouTubeSearcher()

    async def quick_research(self, topic: str) -> dict:
        """Quick 30-second research summary.

        Args:
            topic: Research topic

        Returns:
            Quick summary with 3-5 top resources
        """
        # Run searches with shorter timeouts
        web_results = await self.web_searcher.search(topic, limit=3)
        videos = await self.youtube_searcher.search_videos(topic, limit=2)

        return {
            "topic": topic,
            "overview": f"Research on: {topic}",
            "top_articles": web_results.get("articles", [])[:3],
            "top_videos": videos[:2],
            "estimated_reading_time": 5,
        }
