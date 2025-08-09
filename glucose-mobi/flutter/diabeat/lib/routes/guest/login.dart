import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  AuthState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends AuthState<LoginPage> {
  final _passwordFocus = FocusNode();

  Future<void> _tryLogIn() async {
    setState(() {
      submitted = true;
      validateEmail();
      validatePassword();
      waiting = emailErr == null && passwordErr == null;
    });
    if (!waiting) return;

    final result = await request.logIn(
      context,
      email: emailCtrl.text,
      password: passwordCtrl.text,
    );

    if (result.ok) {
      if (mounted) {
        Navigator.of(context)
          ..pop()
          ..pushReplacementNamed('/home');
      }
    } else {
      _passwordFocus.requestFocus();

      setState(() {
        waiting = false;

        if (!result.haveData) return;

        switch (result.dataAsMap['non_field_errors'][0]) {
          case 'Email does not exist.':
            emailErr = 'Email 不存在';
            break;

          case 'Incorrect password.':
            passwordErr = '密碼錯誤';
            break;
        }
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
          icon: const Icon(Icons.arrow_back_ios_new),
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
                '歡迎回來 !',
                style: TextStyle(fontSize: 35),
                textAlign: TextAlign.center,
              ),
              const Spacer(flex: 1),
              buildEmailField(),
              const SizedBox(height: 20),
              TextField(
                controller: passwordCtrl,
                focusNode: _passwordFocus,
                keyboardType: TextInputType.visiblePassword,
                textInputAction: TextInputAction.send,
                obscureText: passwordObscured,
                decoration: makePasswordDecoration(),
                onChanged: (value) {
                  if (submitted) {
                    setState(validatePassword);
                  }
                },
                onSubmitted: waiting
                    ? null
                    : (value) {
                        _tryLogIn();
                      },
              ),
              const Spacer(flex: 2),
              Row(
                children: [
                  buildScanButton(),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: waiting ? null : _tryLogIn,
                      style: util.filledPageButtonStyle(),
                      icon: const Icon(Icons.login),
                      label: const Text('登入'),
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
