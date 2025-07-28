import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/util.dart';
import 'package:dio/dio.dart';
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
    _usernameErr = username.isEmpty ? 'Username 不能為空' : null;
  }

  Future<void> _tryRegister() async {
    setState(() {
      submitted = true;
      validateEmail();
      _validateUsername();
      validatePassword();
    });

    if (emailErr != null || _usernameErr != null || passwordErr != null) return;

    setState(() => waiting = true);

    try {
      await Request.register(
        context,
        email: emailCtrl.text,
        username: _usernameCtrl.text,
        password: passwordCtrl.text,
        remeberMe: rememberMe,
      );

      if (!mounted) return;
      Navigator.pop(context);
      await Navigator.pushReplacementNamed(context, '/home');
      //
    } on DioException catch (e) {
      setState(() {
        final data = e.response!.data;

        if (data['email'] != null) {
          emailErr = '此 Email 已被使用';
        }
        if (data['username'] != null) {
          _usernameErr = '此 Username 已被使用';
        }
        waiting = false;
      });
    } on CancelConnectionException {
      setState(() => waiting = false);
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
          icon: Icon(Icons.arrow_back_ios_new_rounded),
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
              const SizedBox(height: 20),
              buildRememberMeCheckbox(),
              const Spacer(flex: 2),
              FilledButton(
                onPressed: waiting ? null : _tryRegister,
                style: BtnStyleExt.mainFilled,
                child: const Text('註冊'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
