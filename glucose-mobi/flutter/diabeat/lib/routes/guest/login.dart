import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/util.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  AuthState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends AuthState<LoginPage> {
  Future<void> _tryLogIn() async {
    setState(() {
      submitted = true;
      validateEmail();
      validatePassword();
      waiting = emailErr == null && passwordErr == null;
    });

    if (!waiting) return;

    try {
      await Request.logIn(
        context,
        email: emailCtrl.text,
        password: passwordCtrl.text,
      );

      if (!mounted) return;
      Navigator.pop(context);
      Navigator.pushReplacementNamed(context, '/home');
      //
    } on DioException catch (e) {
      setState(() {
        waiting = false;

        switch (e.type) {
          case DioExceptionType.badResponse:
            final errMsg = e.response!.data['non_field_errors'][0];
            if (errMsg == 'Email does not exist.') {
              emailErr = 'Email 不存在';
            } else if (errMsg == 'Incorrect password.') {
              passwordErr = '密碼錯誤';
            }
            break;

          default:
            break;
        }
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
              buildPasswordField(),
              const Spacer(flex: 2),
              Row(
                children: [
                  buildScanButton(),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton(
                      onPressed: waiting ? null : _tryLogIn,
                      style: PageButtons.filled,
                      child: const Text('登入'),
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
