import 'package:diabeat/routes/connection/request.dart' as request;
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  AuthState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends AuthState<RegisterPage> {
  final _usernameCtrl = TextEditingController();
  String? _usernameErr;

  @override
  void dispose() {
    _usernameCtrl.dispose();
    super.dispose();
  }

  void _validateUsername() {
    final username = _usernameCtrl.text;

    if (username.isEmpty) {
      _usernameErr = 'Username 不能為空';
    } else if (username.length > 30) {
      _usernameErr = 'Username 長度應不超過 30';
    } else {
      _usernameErr = null;
    }
  }

  Future<void> _tryRegister() async {
    setState(() {
      submitted = true;
      validateEmail();
      _validateUsername();
      validatePassword();
      waiting = emailErr == null && _usernameErr == null && passwordErr == null;
    });
    if (!waiting) return;

    final result = await request.register(
      context,
      email: emailCtrl.text,
      username: _usernameCtrl.text,
      password: passwordCtrl.text,
    );
    final data = result.data;

    if (result.ok) {
      if (!mounted) return;
      Navigator.pop(context);
      Navigator.pushReplacementNamed(context, '/home');
      //
    } else {
      setState(() {
        waiting = false;

        if (data == null) return;
        emailErr = switch (data['email']) {
          'Enter a valid email address.' => 'Email 格式不正確',
          'custom user with this email already exists.' => '此 Email 已被使用',
          _ => '錯誤',
        };
        _usernameErr = switch (data['username']) {
          'custom user with this username already exists.' => '此 Username 已被使用',
          _ => '錯誤',
        };
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: Icon(Icons.arrow_back_ios_new),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(flex: 1),
              const Text(
                '歡迎加入 !',
                style: TextStyle(fontSize: 35),
                textAlign: TextAlign.center,
              ),
              const Spacer(flex: 1),
              buildEmailField(),
              const SizedBox(height: 20),
              TextField(
                controller: _usernameCtrl,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: 'Username',
                  errorText: _usernameErr,
                  border: const OutlineInputBorder(),
                ),
                onChanged: (value) {
                  if (submitted) {
                    setState(_validateUsername);
                  }
                },
              ),
              const SizedBox(height: 20),
              buildPasswordField(),
              const Spacer(flex: 2),
              Row(
                children: [
                  buildScanButton(),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton(
                      onPressed: waiting ? null : _tryRegister,
                      style: PageButtons.filled,
                      child: const Text('註冊'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
