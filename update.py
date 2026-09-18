import json
import os

def update_translator():
    path = r'e:\AI\AI Video Translantion and voice cloning platform\modules\translator.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_str = '''    def _parse_translation_response(
        self, response_text: str, segments: List[Dict]
    ) -> List[Dict]:
        \"\"\"Parse translation response from AI.\"\"\"
        try:
            json_str = self._extract_json(response_text)
            data = json.loads(json_str)
            return data.get(\"translations\", [])
        except (json.JSONDecodeError, TypeError, KeyError):
            print(\"[Translator] Failed to parse response, using original text\")
            return [{\"id\": seg[\"id\"], \"text_vi\": seg.get(\"text\", \"\")} for seg in segments]'''

    new_str = '''    def _parse_translation_response(
        self, response_text: str, segments: List[Dict], strict: bool = False
    ) -> List[Dict]:
        \"\"\"Parse translation response from AI.\"\"\"
        try:
            json_str = self._extract_json(response_text)
            data = json.loads(json_str)
            return data.get(\"translations\", [])
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            if strict:
                raise ValueError(f\"Failed to parse JSON: {e}\")
            print(\"[Translator] Failed to parse response, using original text\")
            return [{\"id\": seg[\"id\"], \"text_vi\": seg.get(\"text\", \"\")} for seg in segments]'''
            
    content = content.replace(old_str, new_str)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_metadata_generator():
    path = r'e:\AI\AI Video Translantion and voice cloning platform\modules\metadata_generator.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_generate = '''    def _generate_with_local_llm(self, segments: list, original_title: str) -> Dict:
        client = LocalLLMProvider()
        response_text = client.generate(
            system_prompt=(
                "You are a Vietnamese social-media editor. Return only valid JSON "
                "matching the requested schema."
            ),
            user_prompt=self._metadata_prompt(segments, original_title),
            temperature=0.6,
            max_tokens=1024,
            json_mode=True,
        )
        return self._parse_and_save(response_text, segments)'''

    new_generate = '''    def _generate_with_local_llm(self, segments: list, original_title: str) -> Dict:
        client = LocalLLMProvider()
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response_text = client.generate(
                    system_prompt=(
                        "You are a Vietnamese social-media editor. Return only valid JSON "
                        "matching the requested schema."
                    ),
                    user_prompt=self._metadata_prompt(segments, original_title),
                    temperature=0.6 + (attempt * 0.1),
                    max_tokens=1024,
                    json_mode=True,
                )
                return self._parse_and_save(response_text, segments, strict=True)
            except Exception as e:
                print(f\"[Metadata] Local LLM attempt {attempt + 1} failed: {e}\")
                
        print(\"[Metadata] Local LLM completely failed, using defaults\")
        metadata = self._generate_default_metadata()
        self._save_metadata(metadata)
        self._save_thumbnail_prompts(metadata[\"thumbnail_prompt\"])
        return metadata'''

    old_parse = '''    def _parse_and_save(self, response_text: str, segments: list) -> Dict:
        \"\"\"Parse response and save metadata files.\"\"\"
        try:
            # Extract JSON
            json_str = self._extract_json(response_text)
            metadata = json.loads(json_str)

        except (json.JSONDecodeError, TypeError, ValueError):
            print(\"[Metadata] Failed to parse response, using defaults\")
            metadata = self._generate_default_metadata()'''

    new_parse = '''    def _parse_and_save(self, response_text: str, segments: list, strict: bool = False) -> Dict:
        \"\"\"Parse response and save metadata files.\"\"\"
        try:
            # Extract JSON
            json_str = self._extract_json(response_text)
            metadata = json.loads(json_str)

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            if strict:
                raise ValueError(f\"Failed to parse JSON: {e}\")
            print(\"[Metadata] Failed to parse response, using defaults\")
            metadata = self._generate_default_metadata()'''

    content = content.replace(old_generate, new_generate)
    content = content.replace(old_parse, new_parse)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

update_translator()
update_metadata_generator()
print('Updated both files successfully')
