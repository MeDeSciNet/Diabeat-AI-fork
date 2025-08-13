import 'dart:developer';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  String? _chat;

  @override
  void initState() {
    () async {
      final result = await request.chat(context);

      if (result.ok) {
        setState(() => _chat = result.data['response']['message']['content']);
      } else {
        log('chat failed');
      }
    }();
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: util.backButton(context),
        title: const Text('智慧血糖建議'),
        centerTitle: true,
        actions: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.ios_share)),
        ],
      ),
      body: _chat == null ? Text('haha') : Markdown(data: _chat!),
    );
  }
}
