"""
上下文压缩测试

测试上下文压缩功能
"""

import pytest

from app.services.memory.memory_compressor import (
    ContextCompressor,
    CompressionConfig,
    CompressionStrategy,
    CompressionResult,
)


class TestContextCompressor:
    """上下文压缩器测试"""
    
    def create_test_messages(self, count: int = 10):
        """创建测试消息"""
        messages = []
        for i in range(count):
            messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"这是测试消息 {i}。" * (10 + i),
            })
        return messages
    
    @pytest.mark.asyncio
    async def test_compress_no_messages(self):
        """测试空消息压缩"""
        compressor = ContextCompressor()
        result = await compressor.compress([])
        
        assert result.original_tokens == 0
        assert result.compressed_tokens == 0
        assert result.compression_ratio == 0.0
    
    @pytest.mark.asyncio
    async def test_compress_under_limit(self):
        """测试未超限的压缩"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=10000))
        messages = self.create_test_messages(3)
        
        result = await compressor.compress(messages)
        
        assert result.compression_ratio == 1.0
        assert len(result.compressed_messages) == 3
    
    @pytest.mark.asyncio
    async def test_token_limit_compression(self):
        """测试token限制压缩"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=100))
        messages = self.create_test_messages(10)
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.TOKEN_LIMIT)
        
        assert result.compressed_tokens <= 100
        assert len(result.compressed_messages) <= len(messages)
    
    @pytest.mark.asyncio
    async def test_summary_compression(self):
        """测试摘要压缩"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=100))
        messages = self.create_test_messages(5)
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.SUMMARY)
        
        assert result.compression_ratio < 1.0
        assert result.summary_text is not None
    
    @pytest.mark.asyncio
    async def test_importance_compression(self):
        """测试重要性压缩"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=200))
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "简单问题"},
            {"role": "assistant", "content": "简单回答"},
            {"role": "user", "content": "这是一个非常重要的问题，需要记住关键点"},
            {"role": "assistant", "content": "这是详细的回答内容"},
        ]
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.IMPORTANCE)
        
        assert result.compressed_tokens <= 200
        assert len(result.compressed_messages) > 0
    
    @pytest.mark.asyncio
    async def test_merge_adjacent_compression(self):
        """测试相邻合并压缩"""
        compressor = ContextCompressor(
            CompressionConfig(
                max_tokens=500,
                merge_similarity_threshold=0.2,
            )
        )
        messages = [
            {"role": "user", "content": "你好，我想问一个问题"},
            {"role": "user", "content": "关于Python编程的问题"},
            {"role": "assistant", "content": "好的，请说"},
            {"role": "assistant", "content": "我会尽力帮助你"},
        ]
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.MERGE_ADJACENT)
        
        assert result.compressed_tokens <= 500
    
    @pytest.mark.asyncio
    async def test_truncate_compression(self):
        """测试截断压缩"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=100, preserve_last_n_messages=1))
        messages = self.create_test_messages(10)
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.TRUNCATE)
        
        assert len(result.compressed_messages) <= len(messages)
    
    @pytest.mark.asyncio
    async def test_auto_compression(self):
        """测试自动压缩策略选择"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=500))
        messages = self.create_test_messages(20)
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.AUTO)
        
        assert result.compressed_tokens <= 500
        assert result.strategy in [
            CompressionStrategy.SUMMARY,
            CompressionStrategy.IMPORTANCE,
            CompressionStrategy.MERGE_ADJACENT,
        ]
    
    @pytest.mark.asyncio
    async def test_preserve_system_prompt(self):
        """测试保留系统提示"""
        compressor = ContextCompressor(CompressionConfig(preserve_system_prompt=True))
        messages = [
            {"role": "system", "content": "你是一个专业助手"},
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ]
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.SUMMARY)
        
        system_messages = [m for m in result.compressed_messages if m.get("role") == "system"]
        assert len(system_messages) >= 1
    
    @pytest.mark.asyncio
    async def test_preserve_last_n_messages(self):
        """测试保留最后N条消息"""
        compressor = ContextCompressor(CompressionConfig(preserve_last_n_messages=2))
        messages = self.create_test_messages(10)
        
        result = await compressor.compress(messages, strategy=CompressionStrategy.SUMMARY)
        
        last_original = messages[-2:]
        compressed_content = [m.get("content") for m in result.compressed_messages]
        
        for msg in last_original:
            assert msg["content"] in compressed_content
    
    def test_importance_calculation(self):
        """测试重要性计算"""
        compressor = ContextCompressor()
        
        messages = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "普通问题"},
            {"role": "assistant", "content": "普通回答"},
            {"role": "user", "content": "重要：这是关键信息，必须记住"},
        ]
        
        importances = []
        for i, msg in enumerate(messages):
            importance = compressor._calculate_importance(msg, i, messages)
            importances.append((importance.message_id, importance.importance_score))
        
        importances.sort(key=lambda x: x[1], reverse=True)
        
        assert importances[0][0] == "msg_0" or importances[0][0] == "msg_3"
    
    def test_message_similarity(self):
        """测试消息相似度计算"""
        compressor = ContextCompressor()
        
        msg1 = {"content": "你好，这是一个测试"}
        msg2 = {"content": "你好，这也是一个测试"}
        msg3 = {"content": "完全不同的内容"}
        
        sim12 = compressor._message_similarity(msg1, msg2)
        sim13 = compressor._message_similarity(msg1, msg3)
        
        assert sim12 >= sim13
        assert 0 <= sim12 <= 1
        assert 0 <= sim13 <= 1
    
    def test_truncate_message(self):
        """测试消息截断"""
        compressor = ContextCompressor()
        
        message = {"role": "user", "content": "a" * 1000}
        truncated = compressor._truncate_message(message, 100)
        
        assert len(truncated["content"]) <= 400
        assert truncated.get("_truncated") is True
    
    def test_estimate_tokens(self):
        """测试token估算"""
        compressor = ContextCompressor()
        
        messages = [
            {"content": "Hello World"},  # 约6 chars -> ~1.5 tokens
            {"content": "你好世界"},       # 约4 chars -> ~1 token
        ]
        
        tokens = compressor._estimate_tokens(messages)
        
        assert tokens >= 2
        assert tokens <= 10


class TestCompressionConfig:
    """压缩配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = CompressionConfig()
        
        assert config.strategy == CompressionStrategy.AUTO
        assert config.max_tokens == 4096
        assert config.min_tokens == 1024
        assert config.preserve_system_prompt is True
        assert config.preserve_last_n_messages == 3
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = CompressionConfig(
            strategy=CompressionStrategy.SUMMARY,
            max_tokens=2048,
            preserve_last_n_messages=5,
        )
        
        assert config.strategy == CompressionStrategy.SUMMARY
        assert config.max_tokens == 2048
        assert config.preserve_last_n_messages == 5


class TestCompressionIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_compression_flow(self):
        """测试完整压缩流程"""
        compressor = ContextCompressor(CompressionConfig(max_tokens=50))
        
        messages = [
            {"role": "system", "content": "你是一个编程助手"},
            {"role": "user", "content": "如何在Python中读取文件？"},
            {"role": "assistant", "content": "可以使用open函数打开文件，然后使用read方法读取内容。"},
            {"role": "user", "content": "请给一个完整的例子"},
            {"role": "assistant", "content": "以下是一个完整的例子：\nwith open('file.txt', 'r') as f:\n    content = f.read()\n    print(content)"},
            {"role": "user", "content": "如何处理大文件？"},
            {"role": "assistant", "content": "对于大文件，可以使用readline方法逐行读取，或者使用生成器处理。"},
        ]
        
        result = await compressor.compress(messages)
        
        assert result.compressed_tokens <= 50
        assert len(result.compressed_messages) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
