"""AI-based bookmark organizer using OpenAI-compatible API."""

import json
import logging

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from bookmarks_organizer.models.responses import (
    BookmarkOperation,
    BookmarkWithContent,
    FolderNode,
    OrganizeProposal,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a bookmark organization assistant. Your task is to analyze
a list of bookmarks and propose a logical folder structure.

You MUST respond with valid JSON only, no markdown, no explanation.
The JSON must match this exact schema:
{{
  "proposed_structure": {{
    "name": "root",
    "children": [
      {{
        "name": "Category Name",
        "children": [],
        "bookmark_ids": ["id1", "id2"]
      }}
    ],
    "bookmark_ids": []
  }},
  "operations": [
    {{"op": "create_folder", "bookmark_id": null, "folder_path": ["Category"], "new_title": null}},
    {{"op": "move", "bookmark_id": "id1", "folder_path": ["Category"], "new_title": null}}
  ],
  "warnings": []
}}

Rules:
- Create at most __MAX_FOLDERS__ top-level folders
- Group bookmarks by topic/theme
- Use clear, descriptive folder names
- Every bookmark must be assigned to exactly one folder
- Include create_folder operations before move operations
- folder_path is the path from root to the target folder (list of folder names)
"""

RETRY_PROMPT = """Your previous response was not valid JSON. Please respond with
ONLY valid JSON matching the required schema. No markdown, no explanation."""


class AIOrganizer:
    """Organizes bookmarks using an OpenAI-compatible AI API."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o",
        base_url: str = "https://openrouter.ai/api/v1",
        batch_size: int = 50,
    ) -> None:
        """Initialize with specific configuration values."""
        self._api_key = api_key
        self._model = model
        self._batch_size = batch_size
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def organize(
        self,
        bookmarks: list[BookmarkWithContent],
        max_folders: int = 20,
    ) -> OrganizeProposal:
        """Organize bookmarks into a proposed folder structure."""
        if not bookmarks:
            return OrganizeProposal(
                proposed_structure=FolderNode(name="root"),
                operations=[],
                warnings=[],
            )

        chunks = [
            bookmarks[i : i + self._batch_size]
            for i in range(0, len(bookmarks), self._batch_size)
        ]

        if len(chunks) == 1:
            return await self._organize_chunk(chunks[0], max_folders)

        proposals = []
        for chunk in chunks:
            proposal = await self._organize_chunk(chunk, max_folders)
            proposals.append(proposal)

        return self._merge_proposals(proposals)

    async def _organize_chunk(
        self,
        bookmarks: list[BookmarkWithContent],
        max_folders: int,
    ) -> OrganizeProposal:
        """Send a single chunk of bookmarks to the AI API."""
        bookmark_list = self._format_bookmarks(bookmarks)
        system = SYSTEM_PROMPT_TEMPLATE.replace("__MAX_FOLDERS__", str(max_folders))
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            {"role": "user", "content": bookmark_list},
        ]

        last_error: str = ""
        for attempt in range(3):
            if attempt > 0:
                messages.append({"role": "assistant", "content": last_error})
                messages.append({"role": "user", "content": RETRY_PROMPT})

            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=4096,
                messages=messages,
            )

            raw = response.choices[0].message.content
            if not isinstance(raw, str):
                last_error = "Response was not a string"
                continue
            content = raw
            if content is None or not content.strip():
                last_error = "Response was empty"
                continue

            try:
                data = json.loads(content)
                return OrganizeProposal.model_validate(data)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = content
                logger.warning(
                    "Attempt %d: invalid JSON response: %s",
                    attempt + 1,
                    exc,
                )

        logger.error("Failed to get valid response after 3 attempts")
        return OrganizeProposal(
            proposed_structure=FolderNode(name="root"),
            operations=[],
            warnings=["AI failed to generate valid organization after 3 attempts"],
        )

    def _format_bookmarks(self, bookmarks: list[BookmarkWithContent]) -> str:
        """Format bookmarks as a readable list for the AI prompt."""
        lines = ["Here are the bookmarks to organize:\n"]
        for bm in bookmarks:
            line = f"ID: {bm.id} | Title: {bm.title}"
            if bm.url:
                line += f" | URL: {bm.url}"
            if bm.description:
                line += f" | Desc: {bm.description[:100]}"
            lines.append(line)
        return "\n".join(lines)

    def _merge_proposals(self, proposals: list[OrganizeProposal]) -> OrganizeProposal:
        """Merge multiple batch proposals into one."""
        all_operations: list[BookmarkOperation] = []
        all_warnings: list[str] = []
        root_children: list[FolderNode] = []

        for proposal in proposals:
            all_operations.extend(proposal.operations)
            all_warnings.extend(proposal.warnings)
            root_children.extend(proposal.proposed_structure.children)

        return OrganizeProposal(
            proposed_structure=FolderNode(
                name="root",
                children=root_children,
                bookmark_ids=[],
            ),
            operations=all_operations,
            warnings=all_warnings,
        )
